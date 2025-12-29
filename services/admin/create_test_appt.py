from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from shared.models import Base, User, Appointments, Status, UserRoles

# Connection string (internal docker)
DATABASE_URL = "postgresql://telehealth_user:telehealth_password@telehealth-postgres:5432/telehealth"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    print("Connecting to DB...")
    # Find a patient and a doctor
    patient = db.query(User).filter(User.role == UserRoles.PATIENT).first()
    doctor = db.query(User).filter(User.id == 2).first()

    if not patient or not doctor:
        print("Error: Could not find both patient and doctor.")
        sys.exit(1)

    print(f"Found Patient: {patient.name} (ID: {patient.id})")
    print(f"Found Doctor: {doctor.name} (ID: {doctor.id})")

    now = datetime.now()
    print(f"Creating 5 appointments starting from: {now}")

    for i in range(5):
        appt_time = now + timedelta(minutes=5 + (i * 15)) # 5, 20, 35, 50, 65 mins from now
        
        new_appt = Appointments(
            doctor_id=doctor.id,
            patient_id=patient.id,
            date_time=appt_time,
            status=Status.ACCECPTED, # Typo in model
            booking_source="ai",
            severity=3,
            ai_notes=f"Batch Test Appointment #{i+1}. Patient reports mild symptoms.",
        )
        db.add(new_appt)
        print(f" - Scheduled for {appt_time.strftime('%H:%M')}")

    db.commit()
    db.refresh(new_appt)

    print(f"Successfully created appointment ID: {new_appt.id}")
    print("Check Patient Dashboard now!")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
