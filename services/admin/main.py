from fastapi import Depends, APIRouter, HTTPException, Query, FastAPI
from shared.database import engine, SessionLocal, Base, get_db
from shared import models, schemas, auth_utils as auth
from sqlalchemy.orm import Session

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import logging
import json
# Add these imports at the top
from datetime import datetime, timedelta
from sqlalchemy import func
from typing import Optional
from fastapi import Query
from pathlib import Path
import os
import json
import uvicorn

# Settings Management
from pydantic import BaseModel

router = APIRouter(prefix='/admin', tags=['admin'])
app = FastAPI(title="Admin Service", version="1.0.0")

Base.metadata.create_all(engine)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "admin"}


# === USER MANAGEMENT ===
@router.get('/users/stats')
def get_user_stats(db: Session = Depends(get_db), current_user=Depends(auth.check_admin)):
    """Get comprehensive user statistics"""
    total_users = db.query(models.User).count()
    patients = db.query(models.User).filter(models.User.role == models.UserRoles.PATIENT).count()
    doctors = db.query(models.User).filter(models.User.role == models.UserRoles.DOCTOR).count()
    family = db.query(models.User).filter(models.User.role == models.UserRoles.FAMILY).count()
    admins = db.query(models.User).filter(models.User.role == models.UserRoles.ADMIN).count()
    
    # Recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = db.query(models.User).filter(
        models.User.created_at >= thirty_days_ago
    ).count() if hasattr(models.User, 'created_at') else 0
    
    return {
        "total_users": total_users,
        "breakdown": {
            "patients": patients,
            "doctors": doctors, 
            "family_members": family,
            "admins": admins
        },
        "recent_registrations": recent_registrations
    }

@router.get('/users', response_model=List[schemas.UsersOut])
def get_all_users(
    role: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db), 
    current_user=Depends(auth.check_admin)
):
    """Get paginated users with optional role filtering"""
    query = db.query(models.User)
    
    if role:
        query = query.filter(models.User.role == role)
    
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    
    return users

@router.put('/users/{user_id}/toggle-status')
def toggle_user_status(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(auth.check_admin)
):
    """Enable/disable user account"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Add is_active field to User model if not exists
    if hasattr(user, 'is_active'):
        user.is_active = not user.is_active
        db.commit()
        status = "activated" if user.is_active else "deactivated"
        return {"message": f"User {status} successfully", "user_id": user_id}
    else:
        raise HTTPException(status_code=501, detail="User status toggle not implemented")

@router.delete('/users/{user_id}')
def delete_user(
    user_id: int, 
    current_user=Depends(auth.check_admin), 
    db: Session = Depends(get_db)
):
    """Delete a user and all related data - FIXED CASCADE DELETE"""
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail='User not found')
        
        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail='Cannot delete yourself')
        
        # STEP 1: Delete all family invitations (both sent and received)
        print(f"Deleting family invitations for user {user_id}")
        
        # Delete invitations where user is the inviter
        invitations_sent = db.query(models.FamilyInvitations).filter(
            models.FamilyInvitations.inviter_id == user_id
        ).delete(synchronize_session=False)
        
        # Delete invitations where user is the invitee
        invitations_received = db.query(models.FamilyInvitations).filter(
            models.FamilyInvitations.invitee_id == user_id
        ).delete(synchronize_session=False)
        
        print(f"Deleted {invitations_sent} sent invitations and {invitations_received} received invitations")
        
        # STEP 2: Delete all family connections
        family_connections_as_patient = db.query(models.FamilyConnections).filter(
            models.FamilyConnections.patient_id == user_id
        ).delete(synchronize_session=False)
        
        family_connections_as_family = db.query(models.FamilyConnections).filter(
            models.FamilyConnections.family_member_id == user_id
        ).delete(synchronize_session=False)
        
        print(f"Deleted {family_connections_as_patient} patient connections and {family_connections_as_family} family connections")
        
        # STEP 3: Delete family permissions
        family_permissions = db.query(models.FamilyPermissions).filter(
            models.FamilyPermissions.family_member_id == user_id
        ).delete(synchronize_session=False)
        
        print(f"Deleted {family_permissions} family permissions")
        
        # STEP 4: Delete appointments (both as patient and doctor)
        appointments_as_patient = db.query(models.Appointments).filter(
            models.Appointments.patient_id == user_id
        ).delete(synchronize_session=False)
        
        appointments_as_doctor = db.query(models.Appointments).filter(
            models.Appointments.doctor_id == user_id
        ).delete(synchronize_session=False)
        
        print(f"Deleted {appointments_as_patient} patient appointments and {appointments_as_doctor} doctor appointments")
        
        # STEP 5: Delete vitals (both as patient and doctor)
        vitals_as_patient = db.query(models.Vitals).filter(
            models.Vitals.patient_id == user_id
        ).delete(synchronize_session=False)
        
        vitals_as_doctor = db.query(models.Vitals).filter(
            models.Vitals.doctor_id == user_id
        ).delete(synchronize_session=False)
        
        print(f"Deleted {vitals_as_patient} patient vitals and {vitals_as_doctor} doctor vitals")
        
        # STEP 6: Delete doctor availability settings
        if user.role == models.UserRoles.DOCTOR:
            availability_deleted = db.query(models.DoctorAvailability).filter(
                models.DoctorAvailability.doctor_id == user_id
            ).delete(synchronize_session=False)
            print(f"Deleted {availability_deleted} doctor availability settings")
        
        # STEP 7: Delete chat participants and messages
        # First delete messages sent by this user
        messages_deleted = db.query(models.ChatMessage).filter(
            models.ChatMessage.sender_id == user_id
        ).delete(synchronize_session=False)
        
        # Delete chat participants
        chat_participants_deleted = db.query(models.ChatParticipant).filter(
            models.ChatParticipant.user_id == user_id
        ).delete(synchronize_session=False)
        
        # Delete chat rooms created by this user
        chat_rooms_deleted = db.query(models.ChatRoom).filter(
            models.ChatRoom.created_by == user_id
        ).delete(synchronize_session=False)
        
        print(f"Deleted {messages_deleted} messages, {chat_participants_deleted} chat participants, {chat_rooms_deleted} chat rooms")
        
        # STEP 8: Finally delete the user
        print(f"Deleting user: {user.name} ({user.email})")
        db.delete(user)
        
        # Commit all changes
        db.commit()
        
        return {
            'message': f'User "{user.name}" and all related data deleted successfully',
            'deleted_data': {
                'invitations_sent': invitations_sent,
                'invitations_received': invitations_received,
                'family_connections_as_patient': family_connections_as_patient,
                'family_connections_as_family': family_connections_as_family,
                'family_permissions': family_permissions,
                'appointments_as_patient': appointments_as_patient,
                'appointments_as_doctor': appointments_as_doctor,
                'vitals_as_patient': vitals_as_patient,
                'vitals_as_doctor': vitals_as_doctor,
                'messages_deleted': messages_deleted,
                'chat_participants_deleted': chat_participants_deleted,
                'chat_rooms_deleted': chat_rooms_deleted
            }
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f'Failed to delete user: {str(e)}'
        )
@router.get('/users/{user_id}/details')
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.check_admin)
):
    """Get detailed information about what will be deleted with this user"""
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    
    # Count related data
    family_connections = db.query(models.FamilyConnections).filter(
        (models.FamilyConnections.patient_id == user_id) |
        (models.FamilyConnections.family_member_id == user_id)
    ).count()
    
    family_invitations = db.query(models.FamilyInvitations).filter(
        (models.FamilyInvitations.inviter_id == user_id) |
        (models.FamilyInvitations.invitee_id == user_id)
    ).count()
    
    appointments = db.query(models.Appointments).filter(
        (models.Appointments.patient_id == user_id) |
        (models.Appointments.doctor_id == user_id)
    ).count()
    
    vitals = db.query(models.Vitals).filter(
        (models.Vitals.patient_id == user_id) |
        (models.Vitals.doctor_id == user_id)
    ).count()
    
    chat_participants = db.query(models.ChatParticipant).filter(
        models.ChatParticipant.user_id == user_id
    ).count()
    
    chat_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.sender_id == user_id
    ).count()
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        },
        "related_data": {
            "family_connections": family_connections,
            "family_invitations": family_invitations,
            "appointments": appointments,
            "vitals": vitals,
            "chat_participants": chat_participants,
            "chat_messages": chat_messages
        }
    }

# === APPOINTMENT MANAGEMENT ===
@router.get('/appointments/stats')
def get_appointment_stats(db: Session = Depends(get_db), current_user=Depends(auth.check_admin)):
    """Get appointment statistics"""
    total = db.query(models.Appointments).count()
    pending = db.query(models.Appointments).filter(models.Appointments.status == 'PENDING').count()
    accepted = db.query(models.Appointments).filter(models.Appointments.status == 'ACCEPTED').count()
    rejected = db.query(models.Appointments).filter(models.Appointments.status == 'REJECTED').count()
    completed = db.query(models.Appointments).filter(models.Appointments.status == 'COMPLETED').count()
    
    # Today's appointments
    today = datetime.utcnow().date()
    today_appointments = db.query(models.Appointments).filter(
        func.date(models.Appointments.date_time) == today
    ).count()
    
    return {
        "total_appointments": total,
        "status_breakdown": {
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "completed": completed
        },
        "today_appointments": today_appointments
    }

@router.get('/appointments')
def get_all_appointments(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(auth.check_admin)
):
    """Get all appointments with patient and doctor details"""
    try:
        # Use correct model name 'Appointments'
        query = db.query(models.Appointments).join(
            models.User, models.Appointments.patient_id == models.User.id
        )
        
        if status:
            # Map status string to enum
            if status.upper() == 'PENDING':
                query = query.filter(models.Appointments.status == models.Status.PENDING)
            elif status.upper() == 'ACCEPTED':
                query = query.filter(models.Appointments.status == models.Status.ACCECPTED)
            elif status.upper() == 'REJECTED':
                query = query.filter(models.Appointments.status == models.Status.REJECTED)
        
        offset = (page - 1) * limit
        appointments = query.offset(offset).limit(limit).all()
        
        result = []
        for apt in appointments:
            # Get patient and doctor details
            patient = db.query(models.User).filter(models.User.id == apt.patient_id).first()
            doctor = db.query(models.User).filter(models.User.id == apt.doctor_id).first()
            
            result.append({
                "id": apt.id,
                "patient_name": patient.name if patient else "Unknown",
                "doctor_name": doctor.name if doctor else "Unknown",
                "date_time": apt.date_time,
                "status": apt.status
            })
        
        return result
        
    except Exception as e:
        print(f"Error loading appointments: {e}")
        return []


@router.get('/chats', response_model=List[dict])
def get_all_chats(db: Session = Depends(get_db), current_user=Depends(auth.check_admin)):
    """Get all chat rooms with participant details - FINAL FIX"""
    chats = db.query(models.ChatRoom).all()
    
    result = []
    for chat in chats:
        # Get participants for this chat
        participants = db.query(models.ChatParticipant).filter(
            models.ChatParticipant.chat_id == chat.id
        ).all()
        
        # Get user data for each participant (FIXED)
        participant_data = []
        for participant in participants:
            # Query user separately since relationship is not working
            user = db.query(models.User).filter(
                models.User.id == participant.user_id
            ).first()
            
            if user:
                participant_data.append({
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role
                })
        
        result.append({
            "id": chat.id,
            "name": chat.name,
            "created_by": chat.created_by,
            "participant_count": len(participant_data),
            "participants": participant_data
        })
    
    return result


@router.post("/chats/create")
def create_chat_room(
    name: str,
    participant_ids: List[int],
    db: Session = Depends(get_db), 
    current_user=Depends(auth.check_admin)
):
    """Create chat room with multiple participants"""
    chat = models.ChatRoom(name=name, created_by=current_user.id)
    db.add(chat)
    db.flush()
    
    # Add participants
    for user_id in participant_ids:
        participant = models.ChatParticipant(chat_id=chat.id, user_id=user_id)
        db.add(participant)
    
    db.commit()
    db.refresh(chat)
    
    return {"chat_id": chat.id, "name": name, "message": "Chat room created successfully"}

@router.delete("/chats/{room_id}")
def delete_chat_room(
    room_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(auth.check_admin)
):
    """Delete chat room and all associated data"""
    chat = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Delete participants
    db.query(models.ChatParticipant).filter(models.ChatParticipant.chat_id == room_id).delete()
    
    # Delete messages if Message model exists
    if hasattr(models, 'Message'):
        db.query(models.Message).filter(models.Message.chat_id == room_id).delete()
    
    # Delete chat room
    db.delete(chat)
    db.commit()
    
    return {"message": f"Chat room {room_id} deleted successfully"}

# === SYSTEM MONITORING ===
@router.get('/system/health')
def system_health_check(db: Session = Depends(get_db), current_user=Depends(auth.check_admin)):
    """System health check"""
    try:
        # Database connectivity check
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow()
    }

class SystemSettings(BaseModel):
    max_appointments_per_day: int = 50
    appointment_booking_advance_days: int = 30
    enable_family_permissions: bool = True
    max_chat_participants: int = 10
    enable_vitals_notifications: bool = True

# Global settings (use database in production)
current_settings = SystemSettings()

@router.get('/analytics/overview')
def get_analytics_overview(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(auth.check_admin)
):
    """Get analytics overview - FIXED MODEL NAMES"""
    
    try:
        # Basic counts
        total_users = db.query(models.User).count()
        patients = db.query(models.User).filter(models.User.role == models.UserRoles.PATIENT).count()
        doctors = db.query(models.User).filter(models.User.role == models.UserRoles.DOCTOR).count()
        family = db.query(models.User).filter(models.User.role == models.UserRoles.FAMILY).count()
        
        # FIX: Use correct model name 'Appointments' not 'Appointment'
        total_appointments = db.query(models.Appointments).count()
        
        # Use correct Status enum values (PENDING, ACCECPTED - note the typo in your enum)
        pending_appointments = db.query(models.Appointments).filter(
            models.Appointments.status == models.Status.PENDING
        ).count()
        
        accepted_appointments = db.query(models.Appointments).filter(
            models.Appointments.status == models.Status.ACCECPTED  # Note: Your enum has this typo
        ).count()
        
        # Popular doctors (fixed model name)
        popular_doctors_query = []
        try:
            popular_doctors_query = db.query(
                models.User.name,
                func.count(models.Appointments.id).label('appointment_count')
            ).join(
                models.Appointments, models.User.id == models.Appointments.doctor_id
            ).filter(
                models.User.role == models.UserRoles.DOCTOR
            ).group_by(models.User.id, models.User.name).order_by(
                func.count(models.Appointments.id).desc()
            ).limit(5).all()
        except Exception as e:
            print(f"Error getting popular doctors: {e}")
            popular_doctors_query = []
        
        # Chat and vitals stats
        total_chats = db.query(models.ChatRoom).count()
        total_vitals = db.query(models.Vitals).count()
        
        return {
            "overview": {
                "total_users": total_users,
                "patients": patients,
                "doctors": doctors,
                "family_members": family,
                "total_appointments": total_appointments,
                "pending_appointments": pending_appointments,
                "accepted_appointments": accepted_appointments,
                "total_chats": total_chats,
                "vitals_recorded": total_vitals
            },
            "popular_doctors": [
                {"name": doc[0], "appointment_count": doc[1]} 
                for doc in popular_doctors_query
            ],
            "period_days": days
        }
        
    except Exception as e:
        print(f"Analytics error: {e}")
        # Return safe fallback data
        return {
            "overview": {
                "total_users": 0,
                "patients": 0,
                "doctors": 0,
                "family_members": 0,
                "total_appointments": 0,
                "pending_appointments": 0,
                "accepted_appointments": 0,
                "total_chats": 0,
                "vitals_recorded": 0
            },
            "popular_doctors": [],
            "period_days": days
        }


@router.get('/logs/recent')
def get_recent_logs(
    limit: int = Query(100, ge=1, le=500),
    level: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    current_user=Depends(auth.check_admin)
):
    """Get recent system logs with enhanced parsing - FIXED VERSION"""
    
    os.makedirs("logs", exist_ok=True)
    log_file = Path("logs/telehealth.log")
    
    try:
        logs = []
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Parse recent log lines
            recent_lines = lines[-limit*2:] if len(lines) > limit*2 else lines
            
            for line in reversed(recent_lines):
                line = line.strip()
                if not line:
                    continue
                
                # Parse different log formats - FIXED: Removed self reference
                parsed_log = parse_log_line(line)
                if parsed_log:
                    # Filter by level if specified
                    if level and parsed_log["level"] != level:
                        continue
                    
                    logs.append(parsed_log)
                    
                    if len(logs) >= limit:
                        break
        
        return {
            "logs": logs,
            "total": len(logs),
            "message": "System logs retrieved successfully"
        }
        
    except Exception as e:
        print(f"Error reading logs: {e}")
        return {
            "logs": [{
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "level": "ERROR",
                "message": f"Failed to read logs: {str(e)}",
                "source": "log_reader",
                "ip": "127.0.0.1",
                "method": "GET",
                "path": "/admin/logs/recent",
                "status": "500"
            }],
            "total": 1,
            "error": True
        }

def parse_log_line(line: str) -> dict:
    """Enhanced log line parser - FIXED: Now a standalone function"""
    try:
        # Handle different log formats
        if line.startswith("INFO:") and " - \"" in line:
            # Parse HTTP request logs: INFO:     127.0.0.1:49154 - "GET /path HTTP/1.1" 200 OK
            parts = line.split(" - \"")
            if len(parts) >= 2:
                # Extract IP and port
                ip_part = parts[0].replace("INFO:", "").strip()
                ip_port = ip_part.split(":")
                ip = ip_port[0].strip()
                port = ip_port[1] if len(ip_port) > 1 else ""
                
                # Extract method, path, status
                request_part = parts[1].split("\"")
                if len(request_part) >= 1:
                    request_info = request_part[0].split()
                    method = request_info[0] if len(request_info) > 0 else ""
                    path = request_info[1] if len(request_info) > 1 else ""
                    
                    # Extract status code
                    status_part = parts[1].split("\"")[1].strip() if "\"" in parts[1] else ""
                    status = status_part.split()[0] if status_part else ""
                    
                    return {
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "level": "INFO",
                        "message": f"{method} {path} - {status}",
                        "source": "http",
                        "ip": ip,
                        "port": port,
                        "method": method,
                        "path": path,
                        "status": status
                    }
        
        elif " - " in line and any(level in line for level in ["INFO", "ERROR", "WARNING", "DEBUG"]):
            # Parse custom format logs: 2025-09-30 00:46:12 - api - INFO - GET /path completed
            parts = line.split(" - ")
            if len(parts) >= 3:
                timestamp = parts[0]
                source = parts[1]
                level = parts[2]
                message = " - ".join(parts[3:]) if len(parts) > 3 else ""
                
                return {
                    "timestamp": timestamp,
                    "level": level,
                    "message": message,
                    "source": source,
                    "ip": "127.0.0.1",
                    "method": "",
                    "path": "",
                    "status": ""
                }
        
        return None
        
    except Exception as e:
        return {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "level": "ERROR",
            "message": f"Failed to parse log line: {str(e)}",
            "source": "parser",
            "ip": "",
            "method": "",
            "path": "",
            "status": ""
        }


@router.get('/settings')
def get_system_settings(current_user=Depends(auth.check_admin)):
    """Get current system settings"""
    return current_settings

@router.put('/settings')
def update_system_settings(
    settings: SystemSettings,
    current_user=Depends(auth.check_admin)
):
    """Update system settings"""
    global current_settings
    current_settings = settings
    
    # Log the change
    log_entry = f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - admin - INFO - Settings updated by {current_user.email}"
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/telehealth.log", "a") as f:
            f.write(log_entry + '\n')
    except:
        pass  # Ignore logging errors
    
    return {
        "message": "Settings updated successfully",
        "settings": settings
    }


@router.delete('/chats/{chat_id}/participants')
def remove_all_participants(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.check_admin)
):
    """Remove all participants from a chat room"""
    
    # Check if chat room exists
    chat = db.query(models.ChatRoom).filter(models.ChatRoom.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Remove all participants
    participants_removed = db.query(models.ChatParticipant).filter(
        models.ChatParticipant.chat_id == chat_id
    ).count()
    
    db.query(models.ChatParticipant).filter(
        models.ChatParticipant.chat_id == chat_id
    ).delete()
    
    db.commit()
    
    return {
        "message": f"Removed {participants_removed} participants from chat room '{chat.name}'",
        "participants_removed": participants_removed
    }

@router.get('/chats/{chat_id}/details')
def get_chat_details(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.check_admin)
):
    """Get detailed information about a specific chat room"""
    
    chat = db.query(models.ChatRoom).filter(models.ChatRoom.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Get participants
    participants = db.query(models.ChatParticipant).filter(
        models.ChatParticipant.chat_id == chat_id
    ).all()
    
    participant_details = []
    for participant in participants:
        user = db.query(models.User).filter(
            models.User.id == participant.user_id
        ).first()
        if user:
            participant_details.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            })
    
    # Get message count
    message_count = db.query(models.ChatMessage).filter(
        models.ChatMessage.chat_id == chat_id
    ).count()
    
    return {
        "id": chat.id,
        "name": chat.name,
        "created_by": chat.created_by,
        "participant_count": len(participant_details),
        "participants": participant_details,
        "message_count": message_count
    }

# Mount the router
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
