import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from typing import Optional

from shared.auth_utils import oauth2_schema, verify_token

app = FastAPI(title="API Gateway", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICES = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
    "patient": os.getenv("PATIENT_SERVICE_URL", "http://localhost:8002"),
    "doctor": os.getenv("DOCTOR_SERVICE_URL", "http://localhost:8003"),
    "appointment": os.getenv("APPOINTMENT_SERVICE_URL", "http://localhost:8004"),
    "family": os.getenv("FAMILY_SERVICE_URL", "http://localhost:8005"),
    "chat": os.getenv("CHAT_SERVICE_URL", "http://localhost:8006"),
    "admin": os.getenv("ADMIN_SERVICE_URL", "http://localhost:8007"),
    "triage": os.getenv("WOUND_TRIAGE_SERVICE_URL", "http://localhost:8008"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8009"),
    "records": os.getenv("RECORDS_SERVICE_URL", "http://records-service:8000"),
    "bsp": os.getenv("BSP_SERVICE_URL", "http://localhost:8012"),
    "sms": os.getenv("SMS_SERVICE_URL", "http://sms-service:8000"),
}

# Mount static files (frontend) - uses Docker volume mount
frontend_path = "/app/frontend"
if os.path.exists(frontend_path) and os.listdir(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"Warning: Frontend directory not found or empty at {frontend_path}")


@app.get("/")
async def root():
    """Redirect to frontend"""
    return RedirectResponse(url="/frontend/")

@app.get("/__whoami")
def whoami():
    return {
        "service": "api-gateway",
        "mode": "docker" if os.path.exists("/.dockerenv") else "local"
    }


@app.get("/health")
async def health_check():
    """Gateway health check"""
    return {"status": "healthy", "service": "api-gateway"}


async def proxy_request(
    service_url: str,
    path: str,
    request: Request,
    token: Optional[str] = None
):
    """Proxy request to a service"""
    from fastapi.responses import Response as FastAPIResponse
    
    # Build the full URL
    url = f"{service_url}{path}"
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Prepare headers
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host header
    
    # Add authorization if token provided
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Get request body if present
        body = await request.body()
        
        # Make the request
        try:
            if request.method == "GET":
                response = await client.get(url, headers=headers, params=query_params)
            elif request.method == "POST":
                response = await client.post(url, headers=headers, params=query_params, content=body)
            elif request.method == "PUT":
                response = await client.put(url, headers=headers, params=query_params, content=body)
            elif request.method == "DELETE":
                response = await client.delete(url, headers=headers, params=query_params)
            elif request.method == "OPTIONS":
                response = await client.options(url, headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            # Return FastAPI Response with proper status code
            return FastAPIResponse(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type", "application/json")
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {service_url}"
            )


# Auth Service Routes
# IMPORTANT: Specific routes MUST come before catch-all routes
# Backward-compatible registration endpoints (underscore versions)
@app.api_route("/register_patient", methods=["POST"])
async def register_patient_compat(request: Request):
    """Register patient - backward compatible endpoint"""
    response = await proxy_request(SERVICES["auth"], "/register/patient", request)
    return response


@app.api_route("/register_doctor", methods=["POST"])
async def register_doctor_compat(request: Request):
    """Register doctor - backward compatible endpoint"""
    response = await proxy_request(SERVICES["auth"], "/register/doctor", request)
    return response


@app.api_route("/register_family", methods=["POST"])
async def register_family_compat(request: Request):
    """Register family - backward compatible endpoint"""
    response = await proxy_request(SERVICES["auth"], "/register/family", request)
    return response


# Catch-all registration route (for slash-based URLs)
@app.api_route("/register/{user_type:path}", methods=["POST"])
async def register(user_type: str, request: Request):
    """Register user"""
    response = await proxy_request(SERVICES["auth"], f"/register/{user_type}", request)
    return response


@app.api_route("/token", methods=["POST"])
async def login(request: Request):
    """Login"""
    response = await proxy_request(SERVICES["auth"], "/token", request)
    return response


@app.api_route("/user/me", methods=["GET"])
async def get_current_user(request: Request, token: str = Depends(oauth2_schema)):
    """Get current user"""
    response = await proxy_request(SERVICES["auth"], "/user/me", request, token)
    return response


@app.api_route("/users", methods=["GET"])
async def get_all_users(request: Request, token: str = Depends(oauth2_schema)):
    """Get all users"""
    response = await proxy_request(SERVICES["auth"], "/users", request, token)
    return response


# Doctor Service Routes
@app.api_route("/all_doctors", methods=["GET", "OPTIONS"])
async def get_all_doctors(request: Request):
    """Get all doctors"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], "/doctors", request)
    return response


@app.api_route("/doctors", methods=["GET", "OPTIONS"])
async def get_doctors_alias(request: Request):
    """Get all doctors (alias for /all_doctors)"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], "/doctors", request)
    return response


@app.api_route("/doctor/availability", methods=["GET", "PUT", "OPTIONS"])
async def doctor_availability(request: Request, token: str = Depends(oauth2_schema)):
    """Get or update doctor availability"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], "/doctor/availability", request, token)
    return response


@app.api_route("/doctor/availability/{avail_id}", methods=["DELETE", "OPTIONS"])
async def delete_doctor_availability(avail_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Delete doctor availability"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], f"/doctor/availability/{avail_id}", request, token)
    return response


@app.api_route("/add_vital", methods=["POST", "OPTIONS"])
async def add_vital(request: Request, token: str = Depends(oauth2_schema)):
    """Add patient vital signs (doctor only)"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], "/add_vital", request, token)
    return response


@app.api_route("/doctors/{path:path}", methods=["GET", "PUT", "POST", "OPTIONS"])
async def doctor_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Doctor routes"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], f"/doctors/{path}", request, token)
    return response


@app.api_route("/vitals", methods=["POST", "OPTIONS"])
async def add_vitals(request: Request, token: str = Depends(oauth2_schema)):
    """Add vitals"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["doctor"], "/vitals", request, token)
    return response


@app.post("/ws-token")
async def create_websocket_token(request: Request, token: str = Depends(oauth2_schema)):
    """Generate WebSocket authentication token"""
    from jose import jwt
    from datetime import datetime, timedelta
    
    # Get SECRET_KEY and ALGORITHM from environment or shared config
    # MUST match chat service WS_SECRET_KEY
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    WS_SECRET_KEY = SECRET_KEY + "_ws"
    ALGORITHM = "HS256"
    
    # Verify the access token
    payload = verify_token(token)
    user_id = payload.get("id")
    
    # Create a WebSocket-specific token (same structure, different purpose)
    ws_payload = {
        "sub": str(user_id),  # Chat service expects 'sub' field (string)
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role"),
        "exp": datetime.utcnow() + timedelta(hours=24)  # Longer expiry for WS
    }
    
    ws_token = jwt.encode(ws_payload, WS_SECRET_KEY, algorithm=ALGORITHM)
    return {"ws_token": ws_token}


# Patient Service Routes
# Patient Service Routes
@app.api_route("/patient/appointments", methods=["GET", "OPTIONS"])
async def get_patient_appointments(request: Request, token: str = Depends(oauth2_schema)):
    """Get patient appointments"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["patient"], "/patient/appointments", request, token)
    return response


@app.api_route("/patient/appointments/detailed", methods=["GET", "OPTIONS"])
async def get_patient_appointments_detailed(request: Request, token: str = Depends(oauth2_schema)):
    """Get detailed patient appointments"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["patient"], "/patient/appointments/detailed", request, token)
    return response


@app.api_route("/patient/appointments/{appointment_id}/cancel", methods=["PUT", "OPTIONS"])
async def cancel_patient_appointment(appointment_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Cancel patient appointment"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["patient"], f"/patient/appointments/{appointment_id}/cancel", request, token)
    return response


@app.api_route("/patient/appointments/{appointment_id}/reschedule", methods=["POST", "OPTIONS"])
async def reschedule_patient_appointment(appointment_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Reschedule patient appointment"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["patient"], f"/patient/appointments/{appointment_id}/reschedule", request, token)
    return response


@app.api_route("/patient/{path:path}", methods=["GET", "OPTIONS"])
async def patient_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Patient routes"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["patient"], f"/patients/{path}", request, token)
    return response


@app.api_route("/get_vital", methods=["GET"])
async def get_vitals(request: Request, token: str = Depends(oauth2_schema)):
    """Get patient vitals"""
    response = await proxy_request(SERVICES["patient"], "/get_vital", request, token)
    return response


# Appointment Service Routes
@app.api_route("/create_appointment", methods=["POST", "OPTIONS"])
async def create_appointment(request: Request, token: str = Depends(oauth2_schema)):
    """Create appointment"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/create_appointment", request, token)
    return response


@app.api_route("/get_all_appointments", methods=["GET", "OPTIONS"])
async def get_all_appointments(request: Request, token: str = Depends(oauth2_schema)):
    """Get all appointments"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/get_all_appointments", request, token)
    return response


@app.api_route("/appointment_response", methods=["PUT", "OPTIONS"])
async def appointment_response(request: Request, token: str = Depends(oauth2_schema)):
    """Respond to appointment"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/appointment_response", request, token)
    return response


@app.api_route("/cancel_slot", methods=["POST", "OPTIONS"])
async def cancel_slot(request: Request, token: str = Depends(oauth2_schema)):
    """Cancel appointment slot"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/cancel_slot", request, token)
    return response


@app.api_route("/available_appointment", methods=["GET", "OPTIONS"])
async def get_available_appointments(request: Request):
    """Get available appointments"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/available_appointment", request)
    return response


@app.api_route("/reserve_slot", methods=["POST", "OPTIONS"])
async def reserve_slot(request: Request, token: str = Depends(oauth2_schema)):
    """Reserve slot"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/reserve_slot", request, token)
    return response


@app.api_route("/confirm_slot", methods=["POST", "OPTIONS"])
async def confirm_slot(request: Request, token: str = Depends(oauth2_schema)):
    """Confirm slot"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/confirm_slot", request, token)
    return response


@app.api_route("/find_best_slot", methods=["GET", "OPTIONS"])
async def find_best_slot_proxy(request: Request, token: str = Depends(oauth2_schema)):
    """Find best slot (Auto-Booking)"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/find_best_slot", request, token)
    return response


# Queue Management Routes
@app.api_route("/queue/start-day/{doctor_id}", methods=["POST", "OPTIONS"])
async def start_day(doctor_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Doctor starts their day - auto-queues all appointments"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/start-day/{doctor_id}", request, token)
    return response

@app.api_route("/queue/check-in/{appointment_id}", methods=["POST", "OPTIONS"])
async def queue_check_in(appointment_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Patient check-in for queue"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/check-in/{appointment_id}", request, token)
    return response


@app.api_route("/queue/status/{appointment_id}", methods=["GET", "OPTIONS"])
async def queue_status(appointment_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Get queue status for appointment"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/status/{appointment_id}", request, token)
    return response


@app.api_route("/queue/doctor/{doctor_id}", methods=["GET", "OPTIONS"])
async def get_doctor_queue(doctor_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Get doctor's patient queue"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/doctor/{doctor_id}", request, token)
    return response


@app.api_route("/queue/update-delay", methods=["POST", "OPTIONS"])
async def update_delay(request: Request, token: str = Depends(oauth2_schema)):
    """Doctor reports delay"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], "/queue/update-delay", request, token)
    return response


@app.api_route("/queue/call-next/{doctor_id}", methods=["POST", "OPTIONS"])
async def call_next_patient(doctor_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Doctor calls next patient"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/call-next/{doctor_id}", request, token)
    return response


@app.api_route("/queue/complete-current/{doctor_id}", methods=["POST", "OPTIONS"])
async def complete_current_patient(doctor_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Complete current patient"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/complete-current/{doctor_id}", request, token)
    return response


@app.api_route("/queue/remove/{queue_id}", methods=["DELETE", "OPTIONS"])
async def remove_from_queue(queue_id: int, request: Request, token: str = Depends(oauth2_schema)):
    """Remove patient from queue"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["appointment"], f"/queue/remove/{queue_id}", request, token)
    return response

# Family Service Routes
@app.api_route("/family/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def family_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Family routes"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["family"], f"/{path}", request, token)
    return response


@app.api_route("/invitations/{path:path}", methods=["GET", "POST", "PUT", "OPTIONS"])
async def invitation_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Invitation routes"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["family"], f"/invitations/{path}", request, token)
    return response


# Chat Service Routes (handles both /chat and /chats)
@app.api_route("/chat/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def chat_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Chat routes"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["chat"], f"/{path}", request, token)
    return response

# Chat explicit routes BEFORE catch-all
@app.api_route("/chats/my", methods=["GET", "OPTIONS"])
async def get_my_chats(request: Request, token: str = Depends(oauth2_schema)):
    """Get my chat rooms"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["chat"], "/my", request, token)
    return response


@app.api_route("/chats/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def chats_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Chat routes (catch-all for other /chats paths)"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["chat"], f"/{path}", request, token)
    return response


# Admin Service Routes
@app.api_route("/admin/{path:path}", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def admin_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Admin routes"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["admin"], f"/admin/{path}", request, token)
    return response


    response = await proxy_request(SERVICES["admin"], f"/logs/{path}", request, token)
    return response


# === WEBSOCKET PROXY ===
import asyncio
import websockets
from fastapi import WebSocket, Query

async def websocket_proxy(client_ws: WebSocket, target_url: str):
    """Generic WebSocket Proxy"""
    await client_ws.accept()
    
    try:
        async with websockets.connect(target_url) as server_ws:
            async def forward_client():
                try:
                    while True:
                        # Receive from client
                        message = await client_ws.receive_text()
                        await server_ws.send(message)
                except Exception:
                    pass # Client disconnected

            async def forward_server():
                try:
                    async for message in server_ws:
                        # Receive from server
                        await client_ws.send_text(message)
                except Exception:
                    pass # Server disconnected

            # Run both tasks
            await asyncio.gather(forward_client(), forward_server())
            
    except Exception as e:
        print(f"WebSocket Proxy Error: {e}")
        try:
            await client_ws.close(code=1011)
        except:
            pass


@app.websocket("/ws/doctor/{doctor_id}/slots")
async def ws_doctor_slots_proxy(websocket: WebSocket, doctor_id: int):
    """Proxy for doctor slots WebSocket - Public Access"""
    # Validating token here breaks frontend which doesn't send it.
    # Appointment service allows public access for slot updates.
    
    # 2. Build Target URL
    base = SERVICES["appointment"].replace("http://", "ws://").replace("https://", "wss://")
    target = f"{base}/ws/doctor/{doctor_id}/slots"
    
    # 3. Proxy
    await websocket_proxy(websocket, target)


@app.websocket("/ws/chat/{chat_id}")
async def ws_chat_proxy(websocket: WebSocket, chat_id: int, ws_token: str = Query(None)):
    """Proxy for chat WebSocket"""
    # Note: Chat service expects 'ws_token' and handles validation internally
    if not ws_token:
         await websocket.close(code=1008, reason="Missing ws_token")
         return

    base = SERVICES["chat"].replace("http://", "ws://").replace("https://", "wss://")
    # Chat service route is /ws/{chat_id}?ws_token=...
    target = f"{base}/ws/{chat_id}?ws_token={ws_token}"
    
    await websocket_proxy(websocket, target)

# Also support /chats/ws/... pattern if used
@app.websocket("/chats/ws/{chat_id}")
async def ws_chat_proxy_alt(websocket: WebSocket, chat_id: int, ws_token: str = Query(None)):
    await ws_chat_proxy(websocket, chat_id, ws_token)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Triage Service Routes (Wound API)
@app.api_route("/triage/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def triage_routes(path: str, request: Request):
    """Triage routes (Public/Private handled by service)"""
    if request.method == "OPTIONS":
        return {}
        
    # Triage service might need token for some endpoints, extract if present
    # But wound triage API handles auth internally or public access for some parts
    token = None
    if "Authorization" in request.headers:
        token = request.headers["Authorization"].split(" ")[1]
        
    response = await proxy_request(SERVICES["triage"], f"/triage/{path}", request, token)
    return response

# Notification Service Routes
@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def notification_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """Notification routes (Internal usage or dev testing)"""
    if request.method == "OPTIONS":
        return {}
    response = await proxy_request(SERVICES["notification"], f"/{path}", request, token)
    return response


@app.api_route("/records/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def records_proxy(path: str, request: Request, token: str = Depends(oauth2_schema)):
    if request.method == "OPTIONS":
        return {}
    return await proxy_request(SERVICES["records"], f"/records/{path}", request, token)


@app.api_route("/bsp/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def bsp_routes(path: str, request: Request, token: str = Depends(oauth2_schema)):
    """BSP Toolkit routes"""
    if request.method == "OPTIONS":
        return {}
    return await proxy_request(SERVICES["bsp"], f"/{path}", request, token)


@app.api_route("/sms", methods=["POST", "GET", "OPTIONS"])
async def sms_webhook(request: Request):
    """SMS webhook route - no auth required (called by external gateway)"""
    if request.method == "OPTIONS":
        return {}
    # SMS webhook doesn't need token - it's called by external SMS gateway
    return await proxy_request(SERVICES["sms"], "/sms", request)

