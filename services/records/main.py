from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from shared.database import get_db, Base, engine
from shared.models import PatientRecord, VitalsLog, User, UserRoles
from shared.auth_utils import get_current_user, check_doctor

import os

# Create tables if not exist (auto-migration)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Records Service", docs_url="/docs", openapi_url="/openapi.json")

# ==========================
# Schemas
# ==========================

class SOAPNoteCreate(BaseModel):
    chief_complaint: str
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None

class SOAPNoteResponse(SOAPNoteCreate):
    id: int
    patient_id: int
    doctor_id: int
    created_at: datetime
    doctor_name: Optional[str] = None

    class Config:
        from_attributes = True

class VitalsCreate(BaseModel):
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None
    weight: Optional[float] = None
    oxygen_saturation: Optional[int] = None

class VitalsResponse(VitalsCreate):
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    recorded_at: datetime
    doctor_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==========================
# Endpoints
# ==========================

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "records-service"}

# --- Clinical Notes (SOAP) ---

@app.post("/records/{patient_id}/notes", response_model=SOAPNoteResponse)
def create_visit_note(
    patient_id: int,
    note: SOAPNoteCreate,
    current_user: User = Depends(check_doctor),
    db: Session = Depends(get_db)
):
    """
    Add a visit note (SOAP) for a patient. Only Doctors.
    """
    # Verify patient exists
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    new_record = PatientRecord(
        patient_id=patient_id,
        doctor_id=current_user.id,
        chief_complaint=note.chief_complaint,
        subjective=note.subjective,
        objective=note.objective,
        assessment=note.assessment,
        plan=note.plan
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # Enrich response
    response = SOAPNoteResponse.model_validate(new_record)
    response.doctor_name = current_user.name
    return response


@app.get("/records/{patient_id}/history", response_model=List[SOAPNoteResponse])
def get_patient_history(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full history of SOAP notes.
    Doctors can view any patient. Patients can view only their own.
    """
    if current_user.role == UserRoles.PATIENT and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view medical records")
    
    records = db.query(PatientRecord).filter(PatientRecord.patient_id == patient_id).order_by(PatientRecord.created_at.desc()).all()
    
    # Enrich response with doctor names
    results = []
    for r in records:
        resp = SOAPNoteResponse.model_validate(r)
        if r.doctor:
            resp.doctor_name = r.doctor.name
        results.append(resp)
        
    return results


# --- Vitals Logs ---

@app.post("/records/{patient_id}/vitals", response_model=VitalsResponse)
def log_vitals(
    patient_id: int,
    vitals: VitalsCreate,
    current_user: User = Depends(check_doctor),
    db: Session = Depends(get_db)
):
    """
    Log vitals for a patient. Only Doctors.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    new_vitals = VitalsLog(
        patient_id=patient_id,
        doctor_id=current_user.id,
        bp_systolic=vitals.bp_systolic,
        bp_diastolic=vitals.bp_diastolic,
        heart_rate=vitals.heart_rate,
        temperature=vitals.temperature,
        weight=vitals.weight,
        oxygen_saturation=vitals.oxygen_saturation
    )
    db.add(new_vitals)
    db.commit()
    db.refresh(new_vitals)
    
    resp = VitalsResponse.model_validate(new_vitals)
    resp.doctor_name = current_user.name
    return resp


@app.get("/records/{patient_id}/vitals", response_model=List[VitalsResponse])
def get_vitals_history(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vitals history.
    """
    if current_user.role == UserRoles.PATIENT and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view vitals")
        
    logs = db.query(VitalsLog).filter(VitalsLog.patient_id == patient_id).order_by(VitalsLog.recorded_at.desc()).all()
    
    results = []
    for l in logs:
        resp = VitalsResponse.model_validate(l)
        if l.doctor:
            resp.doctor_name = l.doctor.name
        results.append(resp)
        
    return results
