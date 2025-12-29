from shared.database import SessionLocal
from shared.models import User, Appointments, UserRoles

db = SessionLocal()
print("--- USERS (Doctors) ---")
doctors = db.query(User).filter(User.role == UserRoles.DOCTOR).all()
for d in doctors:
    print(f"ID: {d.id}, Name: {d.name}, Email: {d.email}")

print("\n--- APPOINTMENTS (Last 5) ---")
appts = db.query(Appointments).order_by(Appointments.id.desc()).limit(5).all()
for a in appts:
    print(f"ID: {a.id}, DocID: {a.doctor_id}, PatID: {a.patient_id}, Time: {a.date_time}, Status: {a.status}")
