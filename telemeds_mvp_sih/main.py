from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests

app = FastAPI()

# -----------------------------
# Gateway Config
# -----------------------------
# GATEWAY_URL = "http://192.168.15.75:8080/message"  # Replace with your gateway IP
# USERNAME = "sms"
# PASSWORD = "wiulxwkW"

GATEWAY_URL = "http://192.168.1.9:8080/message"  # Replace with your gateway IP
USERNAME = "sms"
PASSWORD = "VOWArcCl"

# -----------------------------
# Pydantic model for sending
# -----------------------------
class SendSMSRequest(BaseModel):
    phoneNumber: str
    message: str

# -----------------------------
# Utility function to send SMS
# -----------------------------
def send_sms(phone_number: str, message: str):
    payload = {
        "textMessage": {"text": message},
        "phoneNumbers": [phone_number],
    }
    try:
        response = requests.post(
            GATEWAY_URL,
            json=payload,
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# API 1: Manual Send
# -----------------------------
@app.post("/send-sms")
def send_sms_api(req: SendSMSRequest):
    result = send_sms(req.phoneNumber, req.message)
    return {"status": "sent" if "error" not in result else "failed", "response": result}

# -----------------------------
# API 2: Webhook Receiver (Auto Reply)
# -----------------------------
@app.post("/sms")
async def sms_webhook(request: Request):
    data = await request.json()
    print("📩 Incoming SMS Webhook:", data)

    event = data.get("event")
    payload = data.get("payload", {})
    message = payload.get("message")
    phone = payload.get("phoneNumber")

    print(f"📰 Event: {event}")
    print(f"📱 From: {phone}")
    print(f"💬 Message: {message}")

    # --- Auto Reply Logic ---
    if phone and message:
        reply = f"Hello! We got your message: '{message}'"
        result = send_sms(phone, reply)
        print(f"📤 Auto-replied to {phone} with: {reply}")
        return {"status": "ok", "auto_reply": result}

    return {"status": "ignored"}
