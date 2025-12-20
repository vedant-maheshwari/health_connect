import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uvicorn

from shared.database import get_db, engine, Base
from shared import models, schemas
from shared.auth_utils import get_current_user_id

app = FastAPI(title="Patient Service", version="1.0.0")

Base.metadata.create_all(bind=engine)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "patient"}


@app.get("/patients/me", response_model=schemas.UsersOut)
async def get_current_patient(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current patient profile"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    return patient


@app.get("/patients/{patient_id}/vitals")
async def get_patient_vitals(patient_id: int, db: Session = Depends(get_db)):
    """Get patient vitals"""
    vitals = db.query(models.Vitals).filter(
        models.Vitals.patient_id == patient_id
    ).order_by(models.Vitals.timestamp.desc()).all()
    
    return vitals


@app.get("/patients/me/vitals")
async def get_my_vitals(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current patient's vitals"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    vitals = db.query(models.Vitals).filter(
        models.Vitals.patient_id == user_id
    ).order_by(models.Vitals.timestamp.desc()).all()
    
    return vitals


@app.get("/patients/me/appointments/detailed")
async def get_patient_appointments_detailed(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get detailed appointments for current patient"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    appointments = db.query(models.Appointments).filter(
        models.Appointments.patient_id == user_id
    ).all()
    
    # Enrich with doctor details
    detailed_appointments = []
    for appt in appointments:
        doctor = db.query(models.User).filter(models.User.id == appt.doctor_id).first()
        
        detailed_appointments.append({
            "id": appt.id,
            "doctor_id": appt.doctor_id,
            "doctor_name": doctor.name if doctor else "Unknown",
            "doctor_email": doctor.email if doctor else "Unknown",
            "appointment_date": appt.date_time.strftime("%Y-%m-%d") if appt.date_time else "",
            "appointment_time": appt.date_time.strftime("%H:%M") if appt.date_time else "",
            "appointment_day": appt.date_time.strftime("%A") if appt.date_time else "",
            "status": appt.status,
            "status_display": appt.status.upper(),
            "can_cancel": appt.status in [models.Status.PENDING, models.Status.ACCECPTED],
            "created_at": appt.date_time.isoformat() if appt.date_time else ""
        })
    
    return detailed_appointments


@app.get('/get_vital')
async def get_vitals(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get vitals for current patient"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    vitals = db.query(models.Vitals).filter(
        models.Vitals.patient_id == user_id
    ).order_by(models.Vitals.timestamp.desc()).all()
    
    return vitals


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get('/patient/appointments')
async def get_patient_appointments(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get appointments for the current patient"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    appointments = db.query(models.Appointments).filter(
        models.Appointments.patient_id == user_id
    ).all()
    
    return appointments


@app.get('/patient/appointments/detailed')
async def get_patient_appointments_detailed(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get detailed appointments for the current patient with doctor info"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    appointments = db.query(models.Appointments).filter(
        models.Appointments.patient_id == user_id
    ).all()
    
    result = []
    for appointment in appointments:
        doctor_info = db.query(models.User).filter(models.User.id == appointment.doctor_id).first()
        
        result.append({
            "id": appointment.id,
            "doctor_id": appointment.doctor_id,
            "doctor_name": doctor_info.name if doctor_info else "Unknown Doctor",
            "doctor_email": doctor_info.email if doctor_info else "",
            "appointment_date": appointment.date_time.isoformat(),
            "appointment_time": appointment.date_time.strftime("%I:%M %p"),
            "appointment_day": appointment.date_time.strftime("%A, %B %d, %Y"),
            "status": appointment.status.value,
            "status_display": appointment.status.value.title(),
            "can_cancel": appointment.status.value == "pending",
            "created_at": appointment.date_time.isoformat()
        })
    
    # Sort by appointment date (most recent first)
    result.sort(key=lambda x: x["appointment_date"], reverse=True)
    return result


@app.put('/patient/appointments/{appointment_id}/cancel')
async def cancel_patient_appointment(
    appointment_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Cancel a patient appointment"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    appointment = db.query(models.Appointments).filter(
        models.Appointments.id == appointment_id,
        models.Appointments.patient_id == user_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status.value != "pending":
        raise HTTPException(status_code=400, detail="Only pending appointments can be cancelled")
    
    appointment.status = models.Status.CANCELLED
    db.commit()
    db.refresh(appointment)
    
    return {"message": "Appointment cancelled successfully", "appointment_id": appointment_id}


@app.post('/patient/appointments/{appointment_id}/reschedule')
async def reschedule_patient_appointment(
    appointment_id: int,
    reschedule_data: dict,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Reschedule a patient appointment"""
    from datetime import datetime
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    appointment = db.query(models.Appointments).filter(
        models.Appointments.id == appointment_id,
        models.Appointments.patient_id == user_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update appointment date/time
    new_datetime_str = reschedule_data.get("new_datetime") or reschedule_data.get("new_date")
    if not new_datetime_str:
        raise HTTPException(status_code=400, detail="new_datetime or new_date required")
        
    new_datetime = datetime.fromisoformat(new_datetime_str.replace('Z', '+00:00'))
    appointment.date_time = new_datetime
    appointment.status = models.Status.PENDING  # Reset to pending
    
    db.commit()
    db.refresh(appointment)
    
    return {
        "message": "Appointment rescheduled successfully",
        "appointment": {
            "id": appointment.id,
            "doctor_id": appointment.doctor_id,
            "appointment_date": appointment.date_time.isoformat(),
            "status": appointment.status.value
        }
    }
