"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import Base, get_db
from shared import models


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_patient(test_db) -> models.User:
    """Create test patient user"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    patient = models.User(
        name="Test Patient",
        email="patient@test.com",
        hashed_password=pwd_context.hash("testpass123"),
        role=models.UserRoles.PATIENT,
        date_of_birth=datetime(1990, 1, 1)
    )
    test_db.add(patient)
    test_db.commit()
    test_db.refresh(patient)
    return patient


@pytest.fixture
def test_doctor(test_db) -> models.User:
    """Create test doctor user"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    doctor = models.User(
        name="Test Doctor",
        email="doctor@test.com",
        hashed_password=pwd_context.hash("testpass123"),
        role=models.UserRoles.DOCTOR,
        date_of_birth=datetime(1985, 1, 1),
        medical_license="MD12345"
    )
    test_db.add(doctor)
    test_db.commit()
    test_db.refresh(doctor)
    return doctor


@pytest.fixture
def test_family(test_db) -> models.User:
    """Create test family user"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    family = models.User(
        name="Test Family",
        email="family@test.com",
        hashed_password=pwd_context.hash("testpass123"),
        role=models.UserRoles.FAMILY,
        date_of_birth=datetime(1988, 1, 1)
    )
    test_db.add(family)
    test_db.commit()
    test_db.refresh(family)
    return family


@pytest.fixture
def patient_token() -> str:
    """Generate test JWT token for patient"""
    from jose import jwt
    from datetime import datetime, timedelta
    
    # Use actual SECRET_KEY from environment (same as running services)
    SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    ALGORITHM = "HS256"
    
    payload = {
        "id": 1,
        "email": "patient@test.com",
        "role": "patient",
        "exp": datetime.utcnow() + timedelta(hours=24)  # Longer expiry for tests
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
def doctor_token() -> str:
    """Generate test JWT token for doctor"""
    from jose import jwt
    from datetime import datetime, timedelta
    
    # Use actual SECRET_KEY from environment (same as running services)
    SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    ALGORITHM = "HS256"
    
    payload = {
        "id": 2,
        "email": "doctor@test.com",
        "role": "doctor",
        "exp": datetime.utcnow() + timedelta(hours=24)  # Longer expiry for tests
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create async HTTP client for API testing"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        yield client
