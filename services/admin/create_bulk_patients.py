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

# Hardcoded hash for "password" (bcrypt)
default_password_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW" 

try:
    print("Connecting to DB...")
    # Find Doctor
    doctor = db.query(User).filter(User.id == 2).first()
    if not doctor:
        print("Error: Could not find doctor (ID 2).")
        sys.exit(1)

    print(f"Assigning appointments to Doctor: {doctor.name} (ID: {doctor.id})")
    
    print(f"Assigning appointments to Doctor: {doctor.name} (ID: {doctor.id})")
    
    import time
    timestamp = int(time.time())
    now = datetime.now()
    start_time = now + timedelta(minutes=5)

    created_count = 0

    for i in range(1, 6):
        # Unique suffix per run
        suffix = f"{timestamp}_{i}"
        email = f"patient_{suffix}@test.com"
        name = f"Patient {suffix}"
        
        patient = User(
            email=email,
            name=name,
            hashed_password=default_password_hash,
            role=UserRoles.PATIENT,
            date_of_birth="1990-01-01"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        print(f"Created Patient: {name} (ID: {patient.id})")

        # 2. Create Appointment
        appt_time = start_time + timedelta(minutes=(i-1) * 15)
        
        new_appt = Appointments(
            doctor_id=doctor.id,
            patient_id=patient.id,
            date_time=appt_time,
            status=Status.ACCECPTED,
            booking_source="ai_test",
            severity=2,
            ai_notes=f"Auto-test for {name}. created at {now.strftime('%H:%M:%S')}"
        )
        db.add(new_appt)
        created_count += 1
        print(f" - Scheduled for {appt_time.strftime('%H:%M')}")

    db.commit()
    print(f"\n✅ Successfully created {created_count} NEW appointments!")
    print("Doctors can now verify the queue contains different patient names.")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
