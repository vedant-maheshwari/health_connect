# routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import List, Dict
from jose import jwt, JWTError
import models
import schemas as schemas  # or import from your main schemas.py
from database import get_db
import auth
from datetime import datetime

from chat.chat_auth import WS_SECRET_KEY, WS_ALGORITHM  # uses WS_SECRET_KEY defined there

router = APIRouter(prefix="/chats", tags=["chats"])

# In-memory connections per chat_id (for a single worker). Use Redis in production.
connections: Dict[int, List[WebSocket]] = {}

def _decode_ws_token(ws_token: str):
    try:
        payload = jwt.decode(ws_token, WS_SECRET_KEY, algorithms=[WS_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise JWTError("missing sub")
        return int(user_id)
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid ws token")

# @router.post("/create", response_model=schemas.ChatRoomOut)
# def create_chat_room(payload: schemas.CreateChatRoomIn, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
#     # Only doctors can create rooms
#     if current_user.role != models.UserRoles.DOCTOR:
#         raise HTTPException(status_code=403, detail="Only doctors can create chat rooms")

#     # Determine patient_id from participant list
#     patient_id = None
#     for uid in payload.participant_ids:
#         user = db.query(models.User).filter(models.User.id == uid).first()
#         if user and user.role == models.UserRoles.PATIENT:
#             patient_id = uid
#             break

#     # create room with patient_id and doctor_id
#     room = models.ChatRoom(
#         name=payload.name,
#         created_by=current_user.id,
#         patient_id=patient_id,  # Set patient_id
#         doctor_id=current_user.id  # Set doctor_id
#     )
#     db.add(room)
#     db.commit()
#     db.refresh(room)

#     # add participants (include doctor)
#     participant_ids = set(payload.participant_ids)
#     participant_ids.add(current_user.id)

#     participants = []
#     for uid in participant_ids:
#         user_obj = db.query(models.User).filter(models.User.id == uid).first()
#         if not user_obj:
#             # skip if user doesn't exist
#             continue
#         p = models.ChatParticipant(chat_id=room.id, user_id=uid)
#         participants.append(p)

#     if participants:
#         db.add_all(participants)
#         db.commit()

#     return room

@router.post('/create')
def create_chat_room_with_emails(
    chat_data: schemas.ChatCreateWithEmails,
    db: Session = Depends(get_db),
    current_user = Depends(auth.check_doctor)
):
    # Determine patient_id from participant emails
    patient_id = None
    doctor_id = current_user.id  # Doctor is the creator
    
    # Find patient from participants
    for email in chat_data.participant_emails:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user and user.role == models.UserRoles.PATIENT:
            patient_id = user.id
            break  # Use the first patient found
    
    # Create chat room with patient_id and doctor_id
    chat_room = models.ChatRoom(
        name=chat_data.name,
        created_by=current_user.id,
        patient_id=patient_id,  # Set patient_id
        doctor_id=doctor_id     # Set doctor_id
    )
    db.add(chat_room)
    db.flush()  # Get the ID
    
    # Add creator (doctor) as participant
    creator_participant = models.ChatParticipant(
        chat_id=chat_room.id,
        user_id=current_user.id
    )
    db.add(creator_participant)
    
    # Add participants by email
    added_participants = []
    for email in chat_data.participant_emails:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            # Check if already a participant
            existing = db.query(models.ChatParticipant).filter(
                models.ChatParticipant.chat_id == chat_room.id,
                models.ChatParticipant.user_id == user.id
            ).first()
            
            if not existing:
                participant = models.ChatParticipant(
                    chat_id=chat_room.id,
                    user_id=user.id
                )
                db.add(participant)
                added_participants.append(user.email)
    
    db.commit()
    db.refresh(chat_room)
    
    return {
        "id": chat_room.id,
        "name": chat_room.name,
        "created_by": current_user.id,
        "patient_id": chat_room.patient_id,
        "doctor_id": chat_room.doctor_id,
        "participants_added": added_participants
    }

# Update your existing /chats/my endpoint
@router.get('/my')
def get_my_chats(
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat rooms - includes family member access"""
    
    if current_user.role == models.UserRoles.FAMILY:
        # Check permissions first
        permissions = db.query(models.FamilyPermissions).filter(
            models.FamilyPermissions.family_member_id == current_user.id
        ).first()
        
        permission_list = permissions.permissions if permissions else []
        
        if "message_doctor" not in permission_list:
            return []
        
        # Get all patients this family member has access to
        family_connections = db.query(models.FamilyConnections).filter(
            models.FamilyConnections.family_member_id == current_user.id
        ).all()
        
        patient_ids = [fc.patient_id for fc in family_connections]
        
        if patient_ids:
            # Get all chats for these patients
            patient_chats = db.query(models.ChatRoom).filter(
                models.ChatRoom.patient_id.in_(patient_ids)
            ).all()
            
            # Add family member to chats they're not already in (with duplicate prevention)
            for chat in patient_chats:
                existing = db.query(models.ChatParticipant).filter(
                    models.ChatParticipant.chat_id == chat.id,
                    models.ChatParticipant.user_id == current_user.id
                ).first()
                
                if not existing:
                    try:
                        new_participant = models.ChatParticipant(
                            chat_id=chat.id,
                            user_id=current_user.id
                        )
                        db.add(new_participant)
                        db.flush()  # Flush immediately to catch constraint violations
                        print(f"✅ Added family member {current_user.id} to chat {chat.id}")
                    except Exception as e:
                        print(f"⚠️ Skip duplicate for chat {chat.id}: {str(e)[:50]}")
                        db.rollback()
                        # Continue to next chat
            
            try:
                db.commit()
            except Exception as e:
                print(f"❌ Commit failed: {e}")
                db.rollback()
        
        # Get all chats where family member is now a participant
        all_chats = (
            db.query(models.ChatRoom)
            .join(models.ChatParticipant, models.ChatParticipant.chat_id == models.ChatRoom.id)
            .filter(models.ChatParticipant.user_id == current_user.id)
            .all()
        )
        
    else:
        # Existing logic for patients and doctors
        all_chats = (
            db.query(models.ChatRoom)
            .join(models.ChatParticipant, models.ChatParticipant.chat_id == models.ChatRoom.id)
            .filter(models.ChatParticipant.user_id == current_user.id)
            .all()
        )
    
    result = []
    for chat in all_chats:
        result.append({
            "id": chat.id,
            "name": chat.name or "Healthcare Chat",
            "created_by": chat.created_by
        })
    
    return result


@router.get('/family')
def get_my_chats(
    patient_id: int = Query(..., description="Patient ID to filter chat rooms"),
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == models.UserRoles.FAMILY:
        # Check family connection for this patient
        fc = db.query(models.FamilyConnections).filter(
            models.FamilyConnections.patient_id == patient_id,
            models.FamilyConnections.family_member_id == current_user.id
        ).first()
        if not fc:
            return []

        # Check message_doctor permission for THIS patient
        perms = db.query(models.FamilyPermissions).filter(
            models.FamilyPermissions.patient_id == patient_id,
            models.FamilyPermissions.family_member_id == current_user.id
        ).first()

        if not perms or "message_doctor" not in perms.permissions:
            return []

        # Return chats ONLY for this patient and current user
        chats = (
            db.query(models.ChatRoom)
            .join(models.ChatParticipant, models.ChatRoom.id == models.ChatParticipant.chat_id)
            .filter(
                models.ChatRoom.patient_id == patient_id,
                models.ChatParticipant.user_id == current_user.id
            )
            .all()
        )
    else:
        # For doctors or patients, return chats for this patient
        chats = (
            db.query(models.ChatRoom)
            .join(models.ChatParticipant, models.ChatRoom.id == models.ChatParticipant.chat_id)
            .filter(
                models.ChatRoom.patient_id == patient_id,
                models.ChatParticipant.user_id == current_user.id
            )
            .all()
        )

    return [{
        "id": chat.id,
        "name": chat.name or "Healthcare Chat",
        "created_by": chat.created_by
    } for chat in chats]


@router.get("/{chat_id}/messages", response_model=List[schemas.ChatMessageOut])
def get_chat_messages(chat_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # ensure membership
    participant = db.query(models.ChatParticipant).filter(
        models.ChatParticipant.chat_id == chat_id,
        models.ChatParticipant.user_id == current_user.id
    ).first()
    
    # If not a participant and family member, check if they have access and auto-add
    if not participant and current_user.role == models.UserRoles.FAMILY:
        chat_room = db.query(models.ChatRoom).filter(models.ChatRoom.id == chat_id).first()
        if chat_room and chat_room.patient_id:
            family_connection = db.query(models.FamilyConnections).filter(
                models.FamilyConnections.patient_id == chat_room.patient_id,
                models.FamilyConnections.family_member_id == current_user.id
            ).first()
            
            if family_connection:
                permissions = db.query(models.FamilyPermissions).filter(
                    models.FamilyPermissions.family_member_id == current_user.id
                ).first()
                
                permission_list = permissions.permissions if permissions else []
                
                if "message_doctor" in permission_list:
                    # Add family member as participant
                    new_participant = models.ChatParticipant(
                        chat_id=chat_id,
                        user_id=current_user.id
                    )
                    db.add(new_participant)
                    db.commit()
                else:
                    raise HTTPException(status_code=403, detail="No permission to view messages")
            else:
                raise HTTPException(status_code=403, detail="No access to this chat")
        else:
            raise HTTPException(status_code=403, detail="Chat not found")
    elif not participant:
        raise HTTPException(status_code=403, detail="Not a member of this chat")

    messages = db.query(models.ChatMessage).filter(models.ChatMessage.chat_id == chat_id).order_by(models.ChatMessage.timestamp).all()

    out = []
    for m in messages:
        sender = db.query(models.User).filter(models.User.id == m.sender_id).first()
        sender_name = sender.name if sender else "Unknown"
        out.append(schemas.ChatMessageOut(
            id=m.id,
            chat_id=m.chat_id,
            sender_id=m.sender_id,
            sender_name=sender_name,  # Include sender name here
            content=m.content,
            timestamp=m.timestamp.isoformat()
        ))
    return out

@router.websocket("/ws/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: int, ws_token: str = Query(...), db: Session = Depends(get_db)):
    """
    Connect with: ws://host/chats/ws/{chat_id}?ws_token=<short_token>
    The short-lived token is generated by POST /ws-token
    """
    # validate ws_token
    try:
        user_id = _decode_ws_token(ws_token)
    except HTTPException:
        await websocket.close(code=1008)
        return

    # check membership - Updated to handle family members
    participant = db.query(models.ChatParticipant).filter(
        models.ChatParticipant.chat_id == chat_id,
        models.ChatParticipant.user_id == user_id
    ).first()
    
    if not participant:
        # If not a direct participant, check if family member with permissions
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.role == models.UserRoles.FAMILY:
            # Check if family has access to this chat's patient
            chat_room = db.query(models.ChatRoom).filter(models.ChatRoom.id == chat_id).first()
            if chat_room and chat_room.patient_id:
                family_connection = db.query(models.FamilyConnections).filter(
                    models.FamilyConnections.patient_id == chat_room.patient_id,
                    models.FamilyConnections.family_member_id == user_id
                ).first()
                
                if family_connection:
                    # Check permissions
                    permissions = db.query(models.FamilyPermissions).filter(
                        models.FamilyPermissions.family_member_id == user_id
                    ).first()
                    
                    permission_list = permissions.permissions if permissions else []
                    
                    if "message_doctor" in permission_list:
                        # Add family member as participant and continue
                        new_participant = models.ChatParticipant(
                            chat_id=chat_id,
                            user_id=user_id
                        )
                        db.add(new_participant)
                        db.commit()
                    else:
                        await websocket.close(code=1008, reason="No permission")
                        return
                else:
                    await websocket.close(code=1008, reason="No access")
                    return
            else:
                await websocket.close(code=1008, reason="No access")
                return
        else:
            await websocket.close(code=1008, reason="Not a member")
            return

    # accept and register
    await websocket.accept()
    chat_id_int = int(chat_id)
    connections.setdefault(chat_id_int, []).append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content")
            if not content:
                continue

            # save message
            msg = models.ChatMessage(chat_id=chat_id_int, sender_id=user_id, content=content)
            db.add(msg)
            db.commit()
            db.refresh(msg)
            
            sender = db.query(models.User).filter(models.User.id == msg.sender_id).first()
            sender_name = sender.name if sender else "Unknown"

            payload = {
                "id": msg.id,
                "chat_id": msg.chat_id,
                "sender_id": msg.sender_id,
                "sender_name": sender_name,   
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }

            # broadcast to all connections in this chat
            conns = list(connections.get(chat_id_int, []))
            for conn in conns:
                try:
                    await conn.send_json(payload)
                except:
                    pass

    except WebSocketDisconnect:
        if websocket in connections.get(chat_id_int, []):
            connections[chat_id_int].remove(websocket)
    except Exception:
        # ensure cleanup
        if websocket in connections.get(chat_id_int, []):
            connections[chat_id_int].remove(websocket)
        try:
            await websocket.close()
        except:
            pass
