import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uvicorn

from shared.database import get_db, engine, Base
from shared import models, schemas
from shared.auth_utils import create_access_token, get_current_user_id, verify_token

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Auth Service", version="1.0.0")

# Create tables
Base.metadata.create_all(bind=engine)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth"}


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


@app.post("/register/patient", response_model=schemas.UsersOut)
async def register_patient(patient: schemas.InsertPatient, db: Session = Depends(get_db)):
    """Register a new patient"""
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == patient.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new patient
    db_patient = models.User(
        name=patient.name,
        email=patient.email,
        hashed_password=hash_password(patient.password),
        date_of_birth=patient.date_of_birth,
        role=models.UserRoles.PATIENT
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@app.post("/register/doctor", response_model=schemas.UsersOut)
async def register_doctor(doctor: schemas.InsertDoctor, db: Session = Depends(get_db)):
    """Register a new doctor"""
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == doctor.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new doctor
    db_doctor = models.User(
        name=doctor.name,
        email=doctor.email,
        hashed_password=hash_password(doctor.password),
        date_of_birth=doctor.date_of_birth,
        role=models.UserRoles.DOCTOR,
        medical_license=doctor.medical_license
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor


@app.post("/register/family", response_model=schemas.UsersOut)
async def register_family(family: schemas.InsertFamily, db: Session = Depends(get_db)):
    """Register a new family member"""
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == family.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new family member
    db_family = models.User(
        name=family.name,
        email=family.email,
        hashed_password=hash_password(family.password),
        date_of_birth=family.date_of_birth,
        role=models.UserRoles.FAMILY
    )
    db.add(db_family)
    db.commit()
    db.refresh(db_family)
    return db_family


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login - returns JWT token"""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"id": user.id, "email": user.email, "role": user.role}
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id
    }


@app.get("/user/me", response_model=schemas.UsersOut)
async def read_users_me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Get current user information"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{user_id}", response_model=schemas.UsersOut)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID (internal use by other services)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/by-phone/{phone}")
async def get_user_by_phone(phone: str, db: Session = Depends(get_db)):
    """Get user by phone number (for SMS service)"""
    # Clean phone number (remove spaces, dashes)
    clean_phone = phone.replace(" ", "").replace("-", "").replace("+", "")
    
    # Try exact match first
    user = db.query(models.User).filter(models.User.phone_number == phone).first()
    
    # If not found, try without country code
    if not user and len(clean_phone) > 10:
        last_10 = clean_phone[-10:]
        user = db.query(models.User).filter(
            models.User.phone_number.endswith(last_10)
        ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this phone number")
    
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@app.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    """Get all users (admin only)"""
    users = db.query(models.User).all()
    return users


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
