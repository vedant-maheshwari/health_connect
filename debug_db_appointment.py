from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://telehealth_user:telehealth_password@localhost:5432/telehealth"
# Adjust host if needed. If running from host accessing docker, localhost:5432 usually works if mapped.
# In verify checking docker-compose: 5432:5432 is mapped.

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("Connected to DB")
        # Get patient ID for 'vedant@example.com' (assuming this is the user)
        # Or just list all recent appointments
        result = conn.execute(text("SELECT id, patient_id, doctor_id, date_time, status, triage_id, booking_source FROM appointments ORDER BY id DESC LIMIT 5"))
        print("\n--- Recent Appointments ---")
        for row in result:
            print(f"ID: {row[0]}, Patient: {row[1]}, Doctor: {row[2]}, Time: {row[3]} (Type: {type(row[3])}), Status: {row[4]}, TriageID: {row[5]}, Source: {row[6]}")
            if row[3]:
                print(f"   Has TZ? {row[3].tzinfo}")
except Exception as e:
    print(e)
