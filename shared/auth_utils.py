from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

oauth2_schema = OAuth2PasswordBearer(tokenUrl='token')

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_TIME = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_TIME)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """Verify and decode JWT token. Returns payload or raises HTTPException"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired"
        )



from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User, UserRoles

def get_current_user_id(token: str = Depends(oauth2_schema)) -> int:
    """Dependency to get current user ID from token"""
    payload = verify_token(token)
    return payload.get("id")


def get_current_user_payload(token: str = Depends(oauth2_schema)) -> dict:
    """Dependency to get full token payload"""
    return verify_token(token)


def get_current_user(token: str = Depends(oauth2_schema), db: Session = Depends(get_db)) -> User:
    """Get current user from database"""
    payload = verify_token(token)
    user_id = payload.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


def check_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRoles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def check_doctor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRoles.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required"
        )
    return current_user


def check_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRoles.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient access required"
        )
    return current_user


def check_family(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRoles.FAMILY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Family member access required"
        )
    return current_user
