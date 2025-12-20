# routers/chat_auth.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from jose import jwt
from shared import auth_utils as auth  # your existing auth module
from sqlalchemy.orm import Session
from shared.database import get_db

router = APIRouter(tags=["chat-auth"])

# Use a separate key for WS tokens (you can also derive from auth.SECRET_KEY)
WS_SECRET_KEY = getattr(auth, "WS_SECRET_KEY", None)
if not WS_SECRET_KEY:
    if getattr(auth, "SECRET_KEY", None):
        WS_SECRET_KEY = auth.SECRET_KEY + "_ws"
    else:
        WS_SECRET_KEY = "default_ws_secret_key"  # hard-coded fallback

WS_ALGORITHM = getattr(auth, "WS_ALGORITHM", "HS256")
WS_TOKEN_EXPIRE_SECONDS = 60  # short-lived

@router.post("/ws-token")
def generate_ws_token(current_user_id: int = Depends(auth.get_current_user_id)):
    """
    Returns a short-lived token for WebSocket authentication.
    Frontend should POST here with Authorization: Bearer <jwt>
    """
    expire = datetime.utcnow() + timedelta(seconds=WS_TOKEN_EXPIRE_SECONDS)
    payload = {"sub": str(current_user_id), "exp": expire}
    token = jwt.encode(payload, WS_SECRET_KEY, algorithm=WS_ALGORITHM)
    return {"ws_token": token, "expires_in": WS_TOKEN_EXPIRE_SECONDS}
