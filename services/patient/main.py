import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uvicorn
import httpx
import os

from shared.database import get_db, engine, Base
from shared import models, schemas
from shared.auth_utils import get_current_user_id

app = FastAPI(title="Patient Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

# Triage service URL
TRIAGE_SERVICE_URL = os.getenv("WOUND_TRIAGE_SERVICE_URL", "http://localhost:8008")


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


async def fetch_triage_data(triage_id: str, token: str) -> dict:
    """Fetch triage case details from triage service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{TRIAGE_SERVICE_URL}/triage/case/{triage_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch triage data for {triage_id}: {response.status_code}")
                return None
    except Exception as e:
        print(f"Error fetching triage data: {e}")
        return None


@app.get("/patients/me/appointments/detailed")
async def get_patient_appointments_detailed(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get detailed appointments for current patient with embedded triage data"""
    patient = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.PATIENT
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="Only patients can access this endpoint")
    
    appointments = db.query(models.Appointments).filter(
        models.Appointments.patient_id == user_id
    ).order_by(models.Appointments.date_time.desc()).all()
    
    # Build detailed appointments with embedded triage data
    detailed_appointments = []
    for appt in appointments:
        doctor = db.query(models.User).filter(models.User.id == appt.doctor_id).first()
        
        appt_data = {
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
            "created_at": appt.date_time.isoformat() if appt.date_time else "", 
            "date_time": appt.date_time.isoformat() if appt.date_time else "",
            "booking_source": appt.booking_source,
            "severity": appt.severity,
            "ai_notes": appt.ai_notes,
            "triage_id": appt.triage_id,
            "triage_data": None  # Will be populated if triage_id exists
        }
        
        # Robust valid ISO formatting
        def to_iso(dt):
            if not dt: return ""
            # If naive, assume UTC and append Z
            if dt.tzinfo is None:
                return dt.isoformat() + "Z"
            return dt.isoformat()

        appt_data["created_at"] = to_iso(appt.date_time)
        appt_data["date_time"] = to_iso(appt.date_time)
        appt_data["appointment_date"] = appt.date_time.strftime("%Y-%m-%d") if appt.date_time else ""
        # Send raw time string, let frontend handle conversion or format explicitly if needed
        appt_data["appointment_time"] = appt.date_time.strftime("%H:%M") if appt.date_time else ""
        
        # Fetch triage data if triage_id exists
        if appt.triage_id:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        f"{TRIAGE_SERVICE_URL}/internal/triage/{appt.triage_id}"
                    )
                    if response.status_code == 200:
                        appt_data["triage_data"] = response.json()
            except Exception as e:
                print(f"Failed to fetch triage data for {appt.triage_id}: {e}")
                # Continue without triage data rather than failing
        
        detailed_appointments.append(appt_data)
    
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
    
    allowed_statuses = ["pending", "accepted"]
    current_status = appointment.status.value if hasattr(appointment.status, 'value') else appointment.status
    
    if current_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Cannot cancel appointment with status {current_status}")
    
    print(f"DEBUG: Cancelling appointment. models.Status.CANCELLED={models.Status.CANCELLED} value={models.Status.CANCELLED.value}")
    # Force use of lowercase string "cancelled" to match DB enum
    appointment.status = "cancelled"
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
