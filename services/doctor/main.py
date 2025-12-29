import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import uvicorn

from shared.database import get_db, engine, Base
from shared import models, schemas
from shared.auth_utils import get_current_user_id

app = FastAPI(title="Doctor Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup_event():
    print("📍 REGISTERED ROUTES:")
    for route in app.routes:
        print(f"  {route.path} [{','.join(route.methods)}]")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "doctor"}


@app.get("/doctors/me/patients")
async def get_my_patients(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get assigned patients for the current doctor"""
    # Verify doctor
    doctor = db.query(models.User).filter(models.User.id == user_id, models.User.role == models.UserRoles.DOCTOR).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors allow")

    assignments = db.query(models.DoctorPatientAssignment).filter(
        models.DoctorPatientAssignment.doctor_id == user_id
    ).all()
    
    patients = []
    for a in assignments:
        if a.patient:
            patients.append(a.patient)
            
    return patients


@app.post("/doctors/me/patients/{patient_id}")
async def assign_patient(
    patient_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Assign a patient to the current doctor"""
    # Check if already assigned
    existing = db.query(models.DoctorPatientAssignment).filter(
        models.DoctorPatientAssignment.doctor_id == user_id,
        models.DoctorPatientAssignment.patient_id == patient_id
    ).first()
    
    if existing:
        return {"message": "Patient already assigned"}
        
    # Verify patient exists
    patient = db.query(models.User).filter(models.User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    new_assign = models.DoctorPatientAssignment(
        doctor_id=user_id,
        patient_id=patient_id
    )
    db.add(new_assign)
    db.commit()
    return {"message": "Patient assigned successfully"}


@app.get("/doctors/patients/search")
async def search_patients(
    q: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Search for patients by name or email"""
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can search patients")
    
    # Search patients by name or email
    search_term = f"%{q.lower()}%"
    patients = db.query(models.User).filter(
        models.User.role == models.UserRoles.PATIENT,
        (models.User.name.ilike(search_term)) | (models.User.email.ilike(search_term))
    ).limit(10).all()
    
    return patients



@app.get("/doctors")
async def get_all_doctors(db: Session = Depends(get_db)):
    """Get all doctors"""
    doctors = db.query(models.User).filter(models.User.role == models.UserRoles.DOCTOR).all()
    return doctors


@app.get("/doctors/{doctor_id}", response_model=schemas.UsersOut)
async def get_doctor_by_id(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor by ID"""
    doctor = db.query(models.User).filter(
        models.User.id == doctor_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@app.get("/doctors/me/appointments")
async def get_doctor_appointments(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all appointments for the current doctor"""
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    appointments = db.query(models.Appointments).filter(
        models.Appointments.doctor_id == user_id
    ).all()
    
    return appointments


@app.put("/doctors/me/availability")
async def update_doctor_availability(
    availability: schemas.SetAvailabilityRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update doctor availability"""
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    # Delete existing availability
    db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == user_id
    ).delete()
    
    # Add new availability
    for item in availability.availabilities:
        db_availability = models.DoctorAvailability(
            doctor_id=user_id,
            day_of_week=item.day_of_week,
            start_time=item.start_time,
            end_time=item.end_time,
            appointment_duration=item.appointment_duration,
            break_start=item.break_start,
            break_end=item.break_end
        )
        db.add(db_availability)
    
    db.commit()
    
    # Return updated availability
    updated_availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == user_id
    ).all()
    
    return updated_availability


@app.get("/doctors/me/availability")
async def get_doctor_availability(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get doctor availability"""
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == user_id
    ).all()
    
    return availability


@app.get("/doctors/{doctor_id}/availability")
async def get_doctor_availability_by_id(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor availability by doctor ID (for internal use)"""
    availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == doctor_id
    ).all()
    return availability


@app.post("/vitals")
async def add_patient_vitals(
    vital_data: schemas.VitalsCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Add patient vitals (doctor only)"""
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add vitals")
    
    # Get patient by email
    patient = db.query(models.User).filter(
        models.User.email == vital_data.patient_email,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Create vitals record
    db_vital = models.Vitals(
        patient_id=patient.id,
        doctor_id=user_id,
        bp=vital_data.bp,
        heart_rate=vital_data.heart_rate,
        temperature=vital_data.temperature,
        notes=vital_data.notes
    )
    db.add(db_vital)
    db.commit()
    db.refresh(db_vital)
    
    return db_vital


# Alias endpoints for frontend compatibility (singular /doctor instead of plural /doctors)
@app.put("/doctor/availability")
async def update_availability_alias(
    availability: schemas.AvailabilityItem,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update doctor availability (alias endpoint)"""
    from datetime import datetime
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    # Helper function to parse time
    def parse_time(val):
        if isinstance(val, str):
            from datetime import datetime
            return datetime.strptime(val, "%H:%M").time()
        return val
    
    # Check if availability for this day already exists
    existing = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == user_id,
        models.DoctorAvailability.day_of_week == availability.day_of_week
    ).first()
    
    if existing:
        # Update existing
        existing.start_time = parse_time(availability.start_time)
        existing.end_time = parse_time(availability.end_time)
        existing.appointment_duration = availability.appointment_duration
        existing.break_start = parse_time(availability.break_start) if availability.break_start else None
        existing.break_end = parse_time(availability.break_end) if availability.break_end else None
        db.add(existing)
    else:
        # Create new
        new_avail = models.DoctorAvailability(
            doctor_id=user_id,
            day_of_week=availability.day_of_week,
            start_time=parse_time(availability.start_time),
            end_time=parse_time(availability.end_time),
            appointment_duration=availability.appointment_duration,
            break_start=parse_time(availability.break_start) if availability.break_start else None,
            break_end=parse_time(availability.break_end) if availability.break_end else None
        )
        db.add(new_avail)
    
    db.commit()
    return {"message": "Availability updated"}


@app.get("/doctor/availability")
async def get_availability_alias(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get doctor availability (alias endpoint)"""
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    availability_records = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == user_id
    ).all()
    
    if not availability_records:
        return {
            "availabilities": [],
            "message": "No availability settings found. Please set your working hours."
        }
    
    availabilities = []
    for record in availability_records:
        availabilities.append({
            "id": record.id,
            "day_of_week": record.day_of_week,
            "start_time": record.start_time.strftime("%H:%M"),
            "end_time": record.end_time.strftime("%H:%M"),
            "appointment_duration": record.appointment_duration,
            "break_start": record.break_start.strftime("%H:%M") if record.break_start else None,
            "break_end": record.break_end.strftime("%H:%M") if record.break_end else None
        })
    
    return {
        "availabilities": availabilities,
        "doctor_id": doctor.id,
        "doctor_name": doctor.name
    }


@app.delete("/doctor/availability/{avail_id}")
async def delete_availability_alias(
    avail_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete doctor availability (alias endpoint)"""
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.id == avail_id,
        models.DoctorAvailability.doctor_id == user_id
    ).first()
    
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    
    db.delete(availability)
    db.commit()
    return {"message": "Availability deleted successfully"}


@app.post("/add_vital")
async def add_vital(
    vital_data: schemas.VitalsCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Add patient vitals (doctor only)"""
    from datetime import datetime
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add vitals")
    
    # Find patient by email
    patient = db.query(models.User).filter(
        models.User.email == vital_data.patient_email,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail='Patient not found with this email')
    
    # Create vital record with timestamp
    vital_record = models.Vitals(
        patient_id=patient.id,
        doctor_id=user_id,
        bp=vital_data.bp,
        heart_rate=vital_data.heart_rate,
        temperature=vital_data.temperature,
        notes=vital_data.notes,
        timestamp=datetime.utcnow()
    )
    
    db.add(vital_record)
    db.commit()
    db.refresh(vital_record)
    
    return {
        "message": "Vitals added successfully",
        "vital_id": vital_record.id,
        "patient_name": patient.name,
        "timestamp": vital_record.timestamp.isoformat()
    }





if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
