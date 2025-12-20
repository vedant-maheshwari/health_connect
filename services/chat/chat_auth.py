"""
WebSocket authentication utilities for chat service
"""
import os
from datetime import datetime, timedelta
from jose import jwt
from fastapi import APIRouter

router = APIRouter(tags=["chat-auth"])

# Use same SECRET_KEY as main shared auth (hardcoded to match actual deployment)
# This MUST match the SECRET_KEY used in api-gateway for token generation
WS_SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
WS_ALGORITHM = "HS256"
WS_TOKEN_EXPIRE_SECONDS = 60  # short-lived
