"""
SMS Gateway Service
Handles incoming SMS commands and routes to appropriate services.
Enables offline access to the telehealth platform via SMS.
"""
import os
import re
import httpx
import hashlib
import time
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="SMS Gateway Service", version="1.0.0")

# Service URLs (internal Docker network)
AUTH_SERVICE = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
APPOINTMENT_SERVICE = os.getenv("APPOINTMENT_SERVICE_URL", "http://appointment-service:8000")
DOCTOR_SERVICE = os.getenv("DOCTOR_SERVICE_URL", "http://doctor-service:8000")

# SMS Gateway Config (Android SMS Gateway app)
GATEWAY_URL = os.getenv("SMS_GATEWAY_URL", "http://172.20.10.14:8080/message")
GATEWAY_USERNAME = os.getenv("SMS_GATEWAY_USERNAME", "sms")
GATEWAY_PASSWORD = os.getenv("SMS_GATEWAY_PASSWORD", "DtzZ8GAx")

# Deduplication: Track processed messages with timestamps
processed_messages = {}  # {hash: timestamp}
DEDUP_WINDOW_SECONDS = 60  # Ignore duplicate within 60 seconds


class SMSWebhookPayload(BaseModel):
    """Incoming SMS webhook payload"""
    event: str = None
    payload: dict = None


def get_message_hash(phone: str, message: str) -> str:
    """Create unique hash for phone+message combo"""
    content = f"{phone}:{message.strip().upper()}"
    return hashlib.md5(content.encode()).hexdigest()


def is_duplicate(phone: str, message: str) -> bool:
    """Check if this message was recently processed"""
    msg_hash = get_message_hash(phone, message)
    current_time = time.time()
    
    # Clean old entries
    old_hashes = [h for h, t in processed_messages.items() if current_time - t > DEDUP_WINDOW_SECONDS]
    for h in old_hashes:
        del processed_messages[h]
    
    if msg_hash in processed_messages:
        return True
    
    processed_messages[msg_hash] = current_time
    return False


# =====================
# SMS Sending Function
# =====================
def send_sms(phone_number: str, message: str) -> dict:
    """Send SMS via gateway"""
    print(f"[OUTGOING SMS] To: {phone_number}")
    print(f"[OUTGOING SMS] Message: {message}")
    
    payload = {
        "textMessage": {"text": message},
        "phoneNumbers": [phone_number],
    }
    try:
        response = httpx.post(
            GATEWAY_URL,
            json=payload,
            auth=(GATEWAY_USERNAME, GATEWAY_PASSWORD),
            timeout=10
        )
        response.raise_for_status()
        print(f"[OUTGOING SMS] Sent successfully")
        return {"success": True, "response": response.json()}
    except Exception as e:
        print(f"[OUTGOING SMS] Error: {e}")
        return {"success": False, "error": str(e)}


# =====================
# Command Parser
# =====================
def parse_command(message: str) -> tuple:
    """Parse SMS message into command and arguments"""
    message = message.strip().upper()
    parts = message.split(maxsplit=1)
    command = parts[0] if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return command, args


# =====================
# User Lookup by Phone
# =====================
async def get_user_by_phone(phone: str) -> dict:
    """Find user by phone number"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE}/users/by-phone/{phone}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"User lookup error: {e}")
    return None


# =====================
# Command Handlers
# =====================
async def handle_help(phone: str, args: str) -> str:
    """Return list of available commands"""
    return """SMS Commands:
BOOK <doctor> <date> <time>
STATUS - View next appointment
CANCEL <id> - Cancel appointment
DOCTORS - List available doctors
SLOTS <doctor> <date> - Check available slots
HELP - Show this message

Example: BOOK waibhav 25-Dec 10:30
Example: SLOTS waibhav 22-Dec"""


async def handle_status(phone: str, args: str) -> str:
    """Get user's next appointment"""
    user = await get_user_by_phone(phone)
    if not user:
        return "Phone not registered. Please register on the app first."
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{APPOINTMENT_SERVICE}/internal/appointments/patient/{user['id']}",
                timeout=5
            )
            if response.status_code == 200:
                appointments = response.json()
                previous_appointments = []
                
                if appointments:
                    upcoming = [a for a in appointments if a.get('status') == 'pending']
                    previous_appointments = [a for a in appointments if a.get('status') != 'pending']
                    if upcoming or previous_appointments:
                        msg_lines = ["Your Appointments:"]
                        count = 0
                        
                        # Show upcoming first
                        for apt in upcoming:
                            msg_lines.append(f"Upcoming: {apt.get('doctor_name', 'Dr')} ({apt.get('date')} {apt.get('time')}) [ID:{apt.get('id')}]")
                            count += 1
                            if count >= 3: # Max 3 upcoming
                                break
                        
                        # Valid status for previous appointments
                        valid_status = ['completed', 'accepted', 'rejected', 'cancelled']
                        # Then show recent history
                        remaining = 5 - count
                        if remaining > 0:
                            # Reverse to show most recent first
                            for apt in reversed(previous_appointments):
                                if apt.get('status') in valid_status:
                                    msg_lines.append(f"{apt.get('status').title()}: {apt.get('doctor_name', 'Dr')} ({apt.get('date')})")
                                    count += 1
                                    if count >= 5:
                                        break
                                
                        return "\n".join(msg_lines)
                return "No upcoming appointments."
    except Exception as e:
        print(f"Status error: {e}")
    return "Could not fetch appointments. Try again later."


async def handle_doctors(phone: str, args: str) -> str:
    """List available doctors"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DOCTOR_SERVICE}/doctors", timeout=5)
            if response.status_code == 200:
                doctors = response.json()
                if doctors:
                    lines = ["Available Doctors:"]
                    for doc in doctors[:5]:
                        lines.append(f"- {doc.get('name', 'N/A')}")
                    return "\n".join(lines)
    except Exception as e:
        print(f"Doctors error: {e}")
    return "Could not fetch doctors. Try again later."


async def handle_slots(phone: str, args: str) -> str:
    """Check available slots for a doctor on a date"""
    parts = args.split()
    if len(parts) < 2:
        return "Format: SLOTS <doctor> <date>\nExample: SLOTS waibhav 22-Dec"
    
    doctor_query = parts[0].replace("DR", "").replace("Dr", "").replace("dr", "").lower()
    date_str = parts[1]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DOCTOR_SERVICE}/doctors", timeout=5)
            if response.status_code != 200:
                return "Could not fetch doctors."
            
            doctors = response.json()
            doctor = None
            for doc in doctors:
                if doctor_query in doc.get('name', '').lower():
                    doctor = doc
                    break
            
            if not doctor:
                return f"Doctor '{doctor_query}' not found. Send DOCTORS for list."
            
            # Parse date
            try:
                year = datetime.now().year
                date_obj = datetime.strptime(f"{date_str}-{year}", "%d-%b-%Y")
                if date_obj < datetime.now():
                    date_obj = date_obj.replace(year=year + 1)
                date_iso = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                return "Invalid date format. Use: 22-Dec"
            
            slots_response = await client.get(
                f"{APPOINTMENT_SERVICE}/available_slots",
                params={"doctor_id": doctor['id'], "date": date_iso},
                timeout=5
            )
            
            if slots_response.status_code == 200:
                slots = slots_response.json()
                if slots:
                    lines = [f"Slots for {doctor.get('name')} on {date_str}:"]
                    for slot in slots[:8]:
                        lines.append(f"- {slot}")
                    return "\n".join(lines)
                else:
                    return f"No available slots for {doctor.get('name')} on {date_str}."
            else:
                return f"Could not fetch slots. Error: {slots_response.status_code}"
                
    except Exception as e:
        print(f"Slots error: {e}")
    return "Could not fetch slots. Try again later."


async def handle_book(phone: str, args: str) -> str:
    """Book an appointment via SMS"""
    user = await get_user_by_phone(phone)
    if not user:
        return "Phone not registered. Please register on the app first."
    
    parts = args.split()
    if len(parts) < 3:
        return "Format: BOOK <doctor> <date> <time>\nExample: BOOK waibhav 25-Dec 10:30"
    
    doctor_query = parts[0].replace("DR", "").replace("Dr", "").replace("dr", "")
    date_str = parts[1]
    time_str = parts[2]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DOCTOR_SERVICE}/doctors", timeout=5)
            if response.status_code == 200:
                doctors = response.json()
                doctor = None
                for doc in doctors:
                    if doctor_query.lower() in doc.get('name', '').lower():
                        doctor = doc
                        break
                
                if not doctor:
                    return f"Doctor '{doctor_query}' not found. Send DOCTORS for list."
                
                try:
                    year = datetime.now().year
                    date_obj = datetime.strptime(f"{date_str}-{year}", "%d-%b-%Y")
                    if date_obj < datetime.now():
                        date_obj = date_obj.replace(year=year + 1)
                    
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    
                    appointment_datetime = date_obj.replace(hour=hour, minute=minute)
                    
                    book_response = await client.post(
                        f"{APPOINTMENT_SERVICE}/internal/create_appointment",
                        json={
                            "patient_id": user['id'],
                            "doctor_id": doctor['id'],
                            "date_time": appointment_datetime.isoformat(),
                            "severity": 1
                        },
                        timeout=10
                    )
                    
                    if book_response.status_code in [200, 201]:
                        result = book_response.json()
                        return f"Booked!\nDoctor: {doctor.get('name')}\nDate: {date_str}\nTime: {time_str}\nID: {result.get('id', 'N/A')}"
                    else:
                        return f"Booking failed: {book_response.text}"
                except ValueError as e:
                    return "Invalid date/time format. Use: 25-Dec 10:30"
    except Exception as e:
        print(f"Book error: {e}")
    return "Booking failed. Try again later."


async def handle_cancel(phone: str, args: str) -> str:
    """Cancel an appointment"""
    user = await get_user_by_phone(phone)
    if not user:
        return "Phone not registered."
    
    appointment_id = args.strip()
    if not appointment_id:
        return "Format: CANCEL <id>\nExample: CANCEL 123"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{APPOINTMENT_SERVICE}/appointments/{appointment_id}",
                timeout=5
            )
            if response.status_code in [200, 204]:
                return f"Appointment #{appointment_id} cancelled."
            elif response.status_code == 404:
                return f"Appointment #{appointment_id} not found."
    except Exception as e:
        print(f"Cancel error: {e}")
    return "Could not cancel. Try again later."


# =====================
# Command Router
# =====================
COMMANDS = {
    "HELP": handle_help,
    "STATUS": handle_status,
    "DOCTORS": handle_doctors,
    "SLOTS": handle_slots,
    "BOOK": handle_book,
    "CANCEL": handle_cancel,
}


async def process_sms(phone: str, message: str) -> str:
    """Process incoming SMS and return response"""
    command, args = parse_command(message)
    
    handler = COMMANDS.get(command)
    if handler:
        return await handler(phone, args)
    
    return f"Unknown command: {command}\nSend HELP for list of commands."


# =====================
# API Endpoints
# =====================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sms-gateway"}


@app.post("/sms")
async def sms_webhook(request: Request):
    """Receive incoming SMS from gateway and process commands"""
    try:
        # Try JSON first (most common for modern webhooks)
        data = await request.json()
    except Exception:
        # Fallback to form data (common for older SMS gateways)
        try:
            form_data = await request.form()
            # Convert form data to dict for processing
            data = dict(form_data)
        except Exception:
            # Final fallback: read raw body as string (for debugging or simple text)
            body = await request.body()
            print(f"[INCOMING SMS] Failed to parse body: {body}")
            return {"status": "error", "reason": "invalid content type"}

    print(f"[INCOMING SMS] Raw Data: {data}")
    
    event = data.get("event", "")
    payload = data.get("payload", {})
    
    # Handle flat structure (some gateways send fields directly)
    if not payload and ("message" in data or "phoneNumber" in data):
        payload = data
        
    message = payload.get("message", "")
    phone = payload.get("phoneNumber", "")
    
    print(f"[INCOMING SMS] Event: {event}")
    print(f"[INCOMING SMS] From: {phone}")
    print(f"[INCOMING SMS] Message: {message}")
    
    # Only process 'sms:received' events
    # Note: If event is missing but we have phone+message, we might want to process it anyway
    # but for now, let's stick to the structure unless it's clearly different
    if event and event != "sms:received":
        print(f"[INCOMING SMS] Ignoring event: {event}")
        return {"status": "ignored", "reason": f"event {event} not processed"}
    
    if not phone or not message:
        return {"status": "ignored", "reason": "missing phone or message"}
    
    # Check for duplicate
    if is_duplicate(phone, message):
        print(f"[INCOMING SMS] Duplicate detected, ignoring")
        return {"status": "duplicate", "reason": "message already processed"}
    
    # Process command
    response_text = await process_sms(phone, message)
    
    # Send reply
    result = send_sms(phone, response_text)
    
    if not result.get("success", False):
        # If sending failed, remove from dedup cache to allow retry
        # This prevents the user from being blocked if the gateway timed out
        msg_hash = get_message_hash(phone, message)
        if msg_hash in processed_messages:
            del processed_messages[msg_hash]
            print(f"[INCOMING SMS] Sending failed, cleared dedup cache for retry")
    
    return {"status": "ok", "reply_sent": result.get("success", False)}


@app.post("/send")
async def send_sms_api(phone_number: str, message: str):
    """Manual SMS sending endpoint"""
    result = send_sms(phone_number, message)
    return {"status": "sent" if result.get("success") else "failed", "result": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
