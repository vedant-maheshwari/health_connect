import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, Set, Optional
import redis.asyncio as redis
import uvicorn
import asyncio

from shared.database import get_db, engine, Base
from shared import models, schemas
from shared.auth_utils import get_current_user_id
import requests

# Helper to send notifications
def send_notification(user_id: int, message: str, channel: str = "all"):
    try:
        url = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000") + "/send"
        requests.post(url, json={
            "user_id": user_id,
            "message": message,
            "channel": channel
        }, timeout=2) # Short timeout
    except Exception as e:
        print(f"Failed to send notification: {e}")

app = FastAPI(title="Appointment Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

# Redis setup
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

HOLD_TTL = 5 * 60  # 5 minutes

# Utility function to create a unique slot key for Redis
def make_slot_key(doctor_id: int, slot_datetime: datetime) -> str:
    """Create a unique key for a slot reservation in Redis"""
    return f"{doctor_id}:{slot_datetime.isoformat()}"

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, doctor_id: int):
        await websocket.accept()
        if doctor_id not in self.active_connections:
            self.active_connections[doctor_id] = set()
        self.active_connections[doctor_id].add(websocket)

    def disconnect(self, websocket: WebSocket, doctor_id: int):
        if doctor_id in self.active_connections:
            self.active_connections[doctor_id].discard(websocket)
            if not self.active_connections[doctor_id]:
                del self.active_connections[doctor_id]

    async def broadcast_to_doctor(self, doctor_id: int, message: dict):
        if doctor_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[doctor_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected websockets
            for conn in disconnected:
                self.disconnect(conn, doctor_id)

manager = ConnectionManager()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "appointment"}


def check_overlap(start1, end1, start2, end2):
    return max(start1, start2) < min(end1, end2)

async def get_doctor_free_slots(doctor_id: int, date: datetime, db: Session, severity: int = 1):
    """
    Get available appointment slots ensuring no overlap.
    Standard: Doctor's default duration (e.g. 30m)
    Emergency (Severity >= 4): 15m duration (Gap Filling)
    """
    # 1. Get Doctor Settings
    day_to_num = {'Sunday': 0, 'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5, 'Saturday': 6}
    day_num = day_to_num[date.strftime('%A')]
    
    doctor_availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == doctor_id,
        models.DoctorAvailability.day_of_week == day_num
    ).first()
    
    if not doctor_availability:
        return []

    # 2. Determine Booked Intervals
    accepted_appointments = db.query(models.Appointments).filter(
        models.Appointments.doctor_id == doctor_id,
        func.date(models.Appointments.date_time) == date,
        models.Appointments.status.in_([models.Status.ACCECPTED, models.Status.PENDING])
    ).all()
    
    booked_intervals = []
    base_duration = doctor_availability.appointment_duration
    
    for app in accepted_appointments:
        start = app.date_time
        # Determine duration of EXISTING appointment
        dur = base_duration
        if hasattr(app, 'severity') and app.severity and app.severity >= 4:
            dur = 15 # Emergency slot duration
        end = start + timedelta(minutes=dur)
        booked_intervals.append((start, end))

    # 3. Add Redis Holds to Intervals
    pattern = f"slot_hold:doctor:{doctor_id}:{date.isoformat()}T*"
    held_keys = await redis_client.keys(pattern)
    for key in held_keys:
        if isinstance(key, bytes): key = key.decode()
        _, _, _, iso_dt = key.split(":", 3)
        dt = datetime.fromisoformat(iso_dt)
        # Assume hold is for at least 15 mins, conservatively block base_duration
        booked_intervals.append((dt, dt + timedelta(minutes=base_duration)))

    # 4. Generate Candidate Slots
    # If High Severity, we scan every 15 mins. If Low, we scan grid (e.g. 30 mins)
    step_minutes = 15 if severity >= 4 else base_duration
    required_duration = 15 if severity >= 4 else base_duration
    
    available_slots = []
    current_time = datetime.combine(date, doctor_availability.start_time)
    end_of_day = datetime.combine(date, doctor_availability.end_time)
    
    # IST Awareness for filtering past slots
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    # Ensure ist_now is naive for comparison if date is naive
    if ist_now.tzinfo:
        ist_now = ist_now.replace(tzinfo=None)
    
    while current_time + timedelta(minutes=required_duration) <= end_of_day:
        slot_start = current_time
        slot_end = current_time + timedelta(minutes=required_duration)
        
        # Filter past slots logic
        if slot_start < ist_now:
            current_time += timedelta(minutes=step_minutes)
            continue
        
        # Check Overlap with Booked
        is_blocked = False
        for (b_start, b_end) in booked_intervals:
            # Ensure naive for comparison
            if b_start.tzinfo: b_start = b_start.replace(tzinfo=None)
            if b_end.tzinfo: b_end = b_end.replace(tzinfo=None)
            
            if check_overlap(slot_start, slot_end, b_start, b_end):
                 is_blocked = True
                 break
        
        # Check Break
        if not is_blocked and doctor_availability.break_start and doctor_availability.break_end:
             break_start = datetime.combine(date, doctor_availability.break_start)
             break_end = datetime.combine(date, doctor_availability.break_end)
             if max(slot_start, break_start) < min(slot_end, break_end):
                 is_blocked = True

        if not is_blocked:
            available_slots.append(slot_start.time())
            
        current_time += timedelta(minutes=step_minutes)
    
    return available_slots


@app.get("/available_appointment")
async def get_available_appointments(
    doctor_id: int = Query(...),
    app_date: str = Query(...),
    severity: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get available appointment slots"""
    date = datetime.fromisoformat(app_date)
    slots = await get_doctor_free_slots(doctor_id, date, db, severity)
    
    # Convert time objects to strings
    return [slot.strftime("%H:%M:%S") for slot in slots]


@app.get("/available_slots")
async def get_available_slots(
    doctor_id: int = Query(...),
    date: str = Query(...),
    severity: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get available slots for a doctor on a specific date (SMS friendly)"""
    try:
        date_obj = datetime.fromisoformat(date)
    except ValueError:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
    
    slots = await get_doctor_free_slots(doctor_id, date_obj, db, severity)
    
    # Return formatted time strings
    return [slot.strftime("%H:%M") for slot in slots]


@app.get("/find_best_slot")
async def find_best_slot(
    severity: int = Query(1),
    triage_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Find the FIRST available slot across ALL doctors.
    Used for 'Auto-Book' feature.
    """
    # 1. Get all doctors
    doctors = db.query(models.User).filter(models.User.role == models.UserRoles.DOCTOR).all()
    
    if not doctors:
        raise HTTPException(status_code=404, detail="No doctors found in system")
        
    # 2. Search for slots starting from today
    # Limit search to next 7 days for performance
    # Use IST for accurate local time comparison
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    today = ist_now.date()
    current_time_ist = ist_now.time()
    
    best_slot = None
    
    for i in range(7):
        check_date = today + timedelta(days=i)
        
        # Check every doctor for this date
        for doctor in doctors:
            slots = await get_doctor_free_slots(doctor.id, check_date, db, severity)
            
            if slots:
                # Found the earliest slot!
                first_slot_time = slots[0] # List is already sorted by natural availability
                
                # If today, ensure time is in future
                if i == 0:
                    # Filter out past slots for today using IST
                    valid_slots = [s for s in slots if s > current_time_ist]
                    if not valid_slots:
                        continue
                    first_slot_time = valid_slots[0]
                
                return {
                    "doctor_id": doctor.id,
                    "doctor_name": doctor.name,
                    "date": check_date.isoformat(),
                    "time": first_slot_time.strftime("%H:%M:%S"),
                    "severity": severity,
                    "is_gap_slot": (severity >= 4 and first_slot_time.minute % 30 != 0) # Heuristic
                }
    
    raise HTTPException(status_code=404, detail="No slots available in the next 7 days")


from fastapi import Query

def verify_family_permission(db: Session, family_member_id: int, patient_id: int):
    # Check if family connection exists and has permission
    perm = db.query(models.FamilyPermissions).filter(
        models.FamilyPermissions.family_member_id == family_member_id,
        models.FamilyPermissions.patient_id == patient_id
    ).first()
    
    if not perm:
        raise HTTPException(status_code=403, detail="No family relationship found")
        
    if "book_appointments" not in perm.permissions:
         raise HTTPException(status_code=403, detail="No permission to book appointments for this patient")
    return True

@app.post("/reserve_slot")
async def reserve_slot(
    reservation: dict,
    target_patient_id: int = Query(None, alias="user_id"),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Reserve a slot temporarily (5 minutes)"""
    doctor_id = reservation.get("doctor_id")
    # Support both keys (Frontend sends appointment_date)
    slot_datetime_str = reservation.get("slot_datetime") or reservation.get("appointment_date")
    
    # Determine distinct patient_id
    patient_id = target_patient_id if target_patient_id else current_user_id

    # If booking for someone else, verify permission
    if patient_id != current_user_id:
        verify_family_permission(db, current_user_id, patient_id)

    if not slot_datetime_str:
        raise HTTPException(status_code=400, detail="Missing appointment_date or slot_datetime")

    try:
        slot_datetime = datetime.fromisoformat(slot_datetime_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    key = make_slot_key(doctor_id, slot_datetime)
    
    # Try to set the key only if it doesn't exist. Store PATIENT_ID in Redis.
    success = await redis_client.set(key, patient_id, nx=True, ex=HOLD_TTL)
    
    if not success:
        raise HTTPException(status_code=409, detail="Slot already reserved")
    
    # Broadcast update
    await manager.broadcast_to_doctor(doctor_id, {
        "type": "slot_reserved",
        "slot": slot_datetime_str
    })
    
    return {"message": "Slot reserved", "key": key, "expires_in": HOLD_TTL}


@app.post("/confirm_slot")
async def confirm_slot(
    confirmation: dict,
    target_patient_id: int = Query(None, alias="user_id"),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Confirm a reserved slot and create appointment"""
    doctor_id = confirmation.get("doctor_id")
    # Support both keys (Frontend sends appointment_date)
    slot_datetime_str = confirmation.get("slot_datetime") or confirmation.get("appointment_date")
    
    # Determine distinct patient_id
    patient_id = target_patient_id if target_patient_id else current_user_id

    # If booking for someone else, verify permission
    if patient_id != current_user_id:
        verify_family_permission(db, current_user_id, patient_id)
    
    if not slot_datetime_str:
        raise HTTPException(status_code=400, detail="Missing appointment_date or slot_datetime")
    
    try:
        slot_datetime = datetime.fromisoformat(slot_datetime_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    key = make_slot_key(doctor_id, slot_datetime)
    
    # Verify the reservation belongs to this PATIENT
    reserved_user_id = await redis_client.get(key)
    if not reserved_user_id or int(reserved_user_id) != patient_id:
        raise HTTPException(status_code=403, detail="Slot not reserved by this patient")
    
    # Extract optional triage context from confirmation
    severity = confirmation.get("severity", 1)
    triage_id = confirmation.get("triage_id")
    ai_notes = confirmation.get("ai_notes")
    
    # Create appointment for PATIENT
    appointment = models.Appointments(
        patient_id=patient_id,  # Use patient_id
        doctor_id=doctor_id,
        date_time=slot_datetime,
        status=models.Status.PENDING,
        severity=severity,
        triage_id=triage_id,
        ai_notes=ai_notes,
        booking_source="ai" if triage_id else "web"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    # Delete the reservation
    await redis_client.delete(key)
    
    # Broadcast update
    await manager.broadcast_to_doctor(doctor_id, {
        "type": "slot_confirmed",
        "slot": slot_datetime_str
    })
    
    return {"message": "Appointment created", "appointment_id": appointment.id}


@app.put("/appointments/{appointment_id}")
async def update_appointment_status(
    appointment_id: int,
    response: schemas.AppointmentResponse,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update appointment status (accept/reject)"""
    appointment = db.query(models.Appointments).filter(
        models.Appointments.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Verify user is the doctor for this appointment
    if appointment.doctor_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if response.action == 'accept':
        appointment.status = models.Status.ACCECPTED
    else:
        appointment.status = models.Status.REJECTED
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


@app.websocket("/ws/doctor/{doctor_id}/slots")
async def websocket_endpoint(websocket: WebSocket, doctor_id: int):
    """WebSocket for real-time slot updates"""
    await manager.connect(websocket, doctor_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, doctor_id)


@app.post("/create_appointment")
async def create_appointment(
    appointment: schemas.BookAppointment,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new appointment"""
    # Create appointment record
    db_appointment = models.Appointments(
        patient_id=user_id,
        doctor_id=appointment.doctor_id,
        date_time=appointment.appointment_date,
        status=models.Status.PENDING,
        severity=appointment.severity,
        triage_id=appointment.triage_id
    )
    
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    
    # Send Notification
    msg = f"Appointment confirmed with Doctor #{appointment.doctor_id} at {appointment.appointment_date}"
    if appointment.severity and appointment.severity >= 4:
         msg += " [URGENT/PRIORITY]"
    send_notification(user_id, msg)
    
    return {
        "message": "Appointment created successfully",
        "appointment_id": db_appointment.id,
        "status": db_appointment.status.value
    }


class SMSBookingRequest(BaseModel):
    """Request model for SMS-based booking (internal use only)"""
    patient_id: int
    doctor_id: int
    date_time: str
    severity: int = 1


@app.post("/internal/create_appointment")
async def create_appointment_internal(
    request: SMSBookingRequest,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint for SMS service to create appointments.
    Does not require JWT auth - only accessible from internal network.
    """
    # Verify patient exists
    patient = db.query(models.User).filter(models.User.id == request.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify doctor exists
    doctor = db.query(models.User).filter(
        models.User.id == request.doctor_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Parse datetime
    try:
        appointment_dt = datetime.fromisoformat(request.date_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date_time format")
    
    # Create appointment
    db_appointment = models.Appointments(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        date_time=appointment_dt,
        status=models.Status.PENDING,
        severity=request.severity,
        booking_source="sms"
    )
    
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    
    return {
        "message": "Appointment created via SMS",
        "id": db_appointment.id,
        "status": db_appointment.status.value
    }


@app.get("/get_all_appointments")
async def get_all_appointments(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all appointments for the current user (doctor view with calendar format)"""
    from datetime import timedelta
    
    # Check if user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    
    appointments = db.query(models.Appointments).filter(
        models.Appointments.doctor_id == user_id
    ).all()
    
    result = []
    for app in appointments:
        patient = db.query(models.User).filter(models.User.id == app.patient_id).first()
        start = app.date_time
        # Default 30 min duration
        end = start + timedelta(minutes=30)
        
        # Format without timezone to prevent UTC interpretation
        # FullCalendar will treat YYYY-MM-DDTHH:MM:SS (without Z) as local time
        start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%S")
        
        result.append({
            "id": app.id,
            "title": patient.name if patient else "Unknown",
            "start": start_str,
            "end": end_str,
            "status": app.status.value,
            "severity": getattr(app, "severity", 1), 
            "triage_id": getattr(app, "triage_id", None),
            "booking_source": getattr(app, "booking_source", "web"),
            "ai_notes": getattr(app, "ai_notes", None)
        })
    
    return result


@app.put("/appointment_response")
async def appointment_response(
    response: schemas.AppointmentResponse,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Accept or reject an appointment (doctor only)"""
    # Verify user is a doctor
    doctor = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.role == models.UserRoles.DOCTOR
    ).first()
    
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can respond to appointments")
    
    # Get appointment
    appointment = db.query(models.Appointments).filter(
        models.Appointments.id == response.appointment_id,
        models.Appointments.doctor_id == user_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update status
    if response.status.lower() == "accept" or response.status.lower() == "accepted":
        appointment.status = models.Status.ACCECPTED  # Note: keeping the typo from models
    elif response.status.lower() == "reject" or response.status.lower() == "rejected":
        appointment.status = models.Status.REJECTED
    else:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'accept' or 'reject'")
    
    db.commit()
    db.refresh(appointment)
    
    return {
        "message": f"Appointment {response.status}ed successfully",
        "appointment_id": appointment.id,
        "status": appointment.status.value
    }


@app.post("/cancel_slot")
async def cancel_slot(
    cancel_data: dict,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Cancel an appointment slot"""
    appointment_id = cancel_data.get("appointment_id")
    if not appointment_id:
        raise HTTPException(status_code=400, detail="appointment_id required")
    
    # Get appointment
    appointment = db.query(models.Appointments).filter(
        models.Appointments.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user is either the patient or the doctor
    if appointment.patient_id != user_id and appointment.doctor_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have permission to cancel this appointment")
    
    # Cancel the appointment
    appointment.status = models.Status.CANCELLED
    db.commit()
    db.refresh(appointment)
    
    return {
        "message": "Appointment cancelled successfully",
        "appointment_id": appointment.id
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
