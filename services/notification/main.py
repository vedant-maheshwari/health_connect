from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime

# Configure logging to show up in Docker logs clearly
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

app = FastAPI(title="Notification Service")

# --- Schemas ---
class NotificationRequest(BaseModel):
    user_id: int
    user_contact: Optional[str] # Phone or Email
    channel: str # "sms", "email", "whatsapp", "all"
    message: str
    subject: Optional[str] = "Telehealth Update"
    metadata: Optional[dict] = {}

class NotificationResponse(BaseModel):
    status: str
    delivered_channels: List[str]
    timestamp: datetime

# --- Mock Clients ---
class NotificationProvider:
    def send(self, contact: str, message: str, subject: str = None):
        raise NotImplementedError

class MockSMSClient(NotificationProvider):
    def send(self, contact: str, message: str, subject: str = None):
        logger.info(f"📱 [SMS MOCK] Sending to {contact}: \"{message}\"")
        return True

class MockWhatsAppClient(NotificationProvider):
    def send(self, contact: str, message: str, subject: str = None):
        logger.info(f"💬 [WHATSAPP MOCK] Sending to {contact}: \n   >>> {message}")
        return True

class MockEmailClient(NotificationProvider):
    def send(self, contact: str, message: str, subject: str = None):
        logger.info(f"📧 [EMAIL MOCK] To: {contact} | Subject: {subject}\n   Body: {message}")
        return True

# Initialize Providers
sms_client = MockSMSClient()
whatsapp_client = MockWhatsAppClient()
email_client = MockEmailClient()

def process_notification(request: NotificationRequest):
    """Background task to send notifications"""
    channels_sent = []
    
    # Logic to determine contact info (in a real app, we might look up user_id -> phone)
    # Here we assume contact is passed or we default to a placeholder
    contact = request.user_contact or f"User-{request.user_id}"
    
    if request.channel in ["sms", "all"]:
        sms_client.send(contact, request.message)
        channels_sent.append("sms")
        
    if request.channel in ["whatsapp", "all"]:
        whatsapp_client.send(contact, request.message)
        channels_sent.append("whatsapp")
        
    if request.channel in ["email", "all"]:
        email_client.send(contact, request.message, request.subject)
        channels_sent.append("email")
        
    logger.info(f"✅ Notification processed for User {request.user_id} via {channels_sent}")

@app.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: NotificationRequest, 
    background_tasks: BackgroundTasks
):
    """
    Queue a notification to be sent asynchronously.
    """
    # Enqueue the task
    background_tasks.add_task(process_notification, request)
    
    return NotificationResponse(
        status="queued",
        delivered_channels=[request.channel], # Approximate
        timestamp=datetime.now()
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "notification-service"}
