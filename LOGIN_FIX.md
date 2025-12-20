# Frontend Login Fix + Database Migration Guide

## ✅ **Issue 1: Login Redirect - FIXED!**

### Problem
The login endpoint was only returning:
```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

But the frontend JavaScript expected `role` and `user_id` to determine which dashboard to show.

### Solution Applied
Updated `/services/auth/main.py` to return:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "role": "patient",      ← Added
  "user_id": 1             ← Added
}
```

### Test the Fix
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=patient@test.com&password=test123"
```

You should now see `role` and `user_id` in the response!

### Frontend Will Now:
- ✅ Get user role from login response
- ✅ Redirect to correct dashboard:
  - `patient` → `patient_dashboard.html`
  - `doctor` → `doctor_dashboard.html`
  - `family` → `family_dashboard.html`
  - `admin` → `admin_dashboard.html`

---

## 📊 **Issue 2: Database Migration**

### Why Your Old Data Isn't There

Your microservices use **PostgreSQL** (fresh database), while your monolithic app likely used **SQLite** (`telehealth.db` file).

The microservices are running with a completely fresh database - that's why you don't see your old users/appointments.

### Migration Options

#### **Option 1: Fresh Start (Recommended for Testing)**
Just register new users through the frontend or API:
```bash
# Register a doctor
curl -X POST http://localhost:8000/register/doctor \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Dr. Smith",
    "email":"doctor@test.com",
    "password":"test123",
    "date_of_birth":"1980-01-01",
    "medical_license":"MD123456"
  }'

# Register a patient
curl -X POST http://localhost:8000/register/patient \
  -H "Content-Type: application/json" \
  -d '{
    "name":"John Doe",
    "email":"john@test.com",
    "password":"test123",
    "date_of_birth":"1990-01-01"
  }'
```

#### **Option 2: Migrate Existing Data**

If you need your old data, run the migration script:
```bash
cd microservices
./migrate_database.sh
```

Or manually export/import:

**1. Export from SQLite (if that's what your monolith uses):**
```bash
# From the monolith directory
sqlite3 telehealth.db <<EOF
.headers on
.mode csv
.output users_export.csv
SELECT * FROM users;
.output appointments_export.csv
SELECT * FROM appointments;
.quit
EOF
```

**2. Import to PostgreSQL:**
```bash
# Copy exports to microservices directory
cp users_export.csv microservices/
cp appointments_export.csv microservices/

# Import to PostgreSQL
cd microservices
docker-compose exec -T postgres psql -U telehealth_user -d telehealth <<EOF
COPY users FROM '/tmp/users_export.csv' WITH CSV HEADER;
COPY appointments FROM '/tmp/appointments_export.csv' WITH CSV HEADER;
EOF
```

#### **Option 3: Point Microservices to SQLite (Temporary)**

Quick way to use old data:

1. **Update `.env`:**
```bash
# Change this line:
DATABASE_URL=postgresql://telehealth_user:telehealth_password@postgres:5432/telehealth

# To this:
DATABASE_URL=sqlite:///./telehealth.db
```

2. **Mount SQLite file in docker-compose.yml:**
```yaml
services:
  auth-service:
    volumes:
      - ../telehealth.db:/app/telehealth.db
```

3. **Restart:**
```bash
docker-compose restart
```

⚠️ **Note**: SQLite isn't ideal for production microservices (doesn't handle concurrent connections well).

---

## 🎯 **Quick Test Commands**

**Test login with role**:
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=patient@test.com&password=test123"
```

**Register a doctor to test doctor dashboard**:
```bash
curl -X POST http://localhost:8000/register/doctor \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Dr. Test",
    "email":"drtest@test.com",
    "password":"test123",
    "date_of_birth":"1975-05-15",
    "medical_license":"MD999999"
  }'
```

**Then login as doctor**:
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=drtest@test.com&password=test123"
```

Should redirect to `doctor_dashboard.html`!

---

## ✅ **Summary**

1. **Login redirect** - Fixed by adding `role` and `user_id` to token response
2. **Database migration** - Choose your approach:
   - Fresh start (easiest for testing)
   - Migrate old data (for production)
   - Temporarily use SQLite (quick fix)

**Try logging in now - it should redirect correctly!** 🎉
