from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.models import Token, TokenData, User, UserInDB
from app.services import get_user_by_username

# Security Configuration
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"🔍 DEBUG AUTH: Decoding token with SECRET_KEY={SECRET_KEY[:10]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ DEBUG AUTH: Token decoded successfully. Payload: id={payload.get('id')}, email={payload.get('email')}, role={payload.get('role')}")
        
        # Main auth system uses 'email' and 'id', not 'sub'
        username: str = payload.get("email") or payload.get("sub")
        role: str = payload.get("role")
        user_id = payload.get("id")
        
        if username is None:
            print("❌ DEBUG AUTH: username/email is None in payload")
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError as e:
        print(f"❌ DEBUG AUTH: JWTError: {e}")
        raise credentials_exception
    
    # Stateless Validation: Trust the token contents (claims)
    # Triage service does not have access to the main Postgres User DB
    return User(
        username=token_data.username,
        role=token_data.role or "doctor",
        full_name=token_data.username
    )

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_doctor(current_user: User = Depends(get_current_active_user)):
    # Case-insensitive check - main system uses uppercase (DOCTOR, ADMIN)
    if current_user.role.upper() not in ["DOCTOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

async def get_current_admin(current_user: User = Depends(get_current_active_user)):
    # Case-insensitive check
    if current_user.role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user
