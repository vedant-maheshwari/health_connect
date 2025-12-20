from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models, schemas, auth, crud
from database import engine, Base, get_db
from family.crud import send_invitation, respond_invitation

router = APIRouter(prefix="/family", tags=["Family"])
Base.metadata.create_all(engine)


@router.get("/permissions/my")
def get_my_family_permissions(
    current_user=Depends(auth.get_current_user), db: Session = Depends(get_db)
):
    conns = (
        db.query(models.FamilyConnections)
        .filter(models.FamilyConnections.family_member_id == current_user.id)
        .all()
    )
    out = []
    for c in conns:
        perms = (
            db.query(models.FamilyPermissions)
            .filter(
                models.FamilyPermissions.patient_id == c.patient_id,
                models.FamilyPermissions.family_member_id == current_user.id,
            )
            .first()
        )
        plist = perms.permissions if perms else []
        out.append(
            {
                "patient_id": c.patient_id,
                "patient_name": c.patient.name,
                "relationship_type": c.relationship_type,
                "permissions": {
                    "can_view_records": "view_records" in plist,
                    "can_book_appointments": "book_appointments" in plist,
                    "can_message_doctor": "message_doctor" in plist,
                    "can_view_vitals": "view_vitals" in plist,
                    "can_manage_family": "manage_family" in plist,
                },
            }
        )
    return out



@router.post("/send_invitation")
def send_invitation_route(
    request: schemas.InvitationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    invitation = send_invitation(
        db, current_user.id, request.invitee_email, request.relationship_type
    )
    if not invitation:
        raise HTTPException(404, detail="Invitation not found")
    return {"token": invitation.token, "status": invitation.status}


@router.put("/respond_invitation")
def respond_invitation_route(
    response: schemas.InvitationResponse, db: Session = Depends(get_db)
):
    result = respond_invitation(db, response.token, response.action)
    if not result:
        raise HTTPException(404, detail="Invitation not found")
    return {"status": response.action}


@router.get("/family_invitation_table")
def family_invitation_table(db: Session = Depends(get_db)):
    invitations = db.query(models.FamilyInvitations).all()
    return [
        {
            "id": inv.id,
            "inviter_id": inv.inviter_id,
            "invitee_id": inv.invitee_id,
            "relationship_type": inv.relationship_type,
            "token": inv.token,
            "status": inv.status.name,
        }
        for inv in invitations
    ]


@router.get(
    "/family_invitation_for_current_user", response_model=List[schemas.InvitationOut]
)
def family_invitation_for_current_user(
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    invitations = (
        db.query(models.FamilyInvitations)
        .filter(
            models.FamilyInvitations.invitee_id == current_user.id,
            models.FamilyInvitations.status == "pending",
        )
        .all()
    )
    return [
        {
            "id": inv.id,
            "inviter_name": (db.query(models.User).get(inv.inviter_id).name),
            "relationship_type": inv.relationship_type,
            "token": inv.token,
        }
        for inv in invitations
    ]


@router.delete("/family_invitation/{invitation_id}", status_code=204)
def delete_invitation(invitation_id: int, db: Session = Depends(get_db)):
    invitation = (
        db.query(models.FamilyInvitations)
        .filter(models.FamilyInvitations.id == invitation_id)
        .first()
    )
    if not invitation:
        raise HTTPException(404, detail="Invitation not found")
    db.delete(invitation)
    db.commit()
    return {"detail": "Invitation deleted successfully"}


@router.get("/get_all_family_members")
def get_all_family_members(current_user=Depends(auth.get_current_user)):
    return [
        {
            "id": conn.family_member.id,
            "name": conn.family_member.name,
            "relationship_type": conn.relationship_type,
        }
        for conn in current_user.family_connections
    ]


@router.get("/get_related_family_members")
def get_related_family_members(current_user=Depends(auth.get_current_user)):
    return [
        {
            "id": conn.family_member.id,
            "name": conn.family_member.name,
            "relationship_type": conn.relationship_type,
        }
        for conn in current_user.related_as_family
    ]


@router.get("/permissions/{patient_id}")
def get_family_permissions(
    patient_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    is_patient = current_user.id == patient_id
    is_family_member = (
        db.query(models.FamilyConnections)
        .filter(
            models.FamilyConnections.patient_id == patient_id,
            models.FamilyConnections.family_member_id == current_user.id,
        )
        .first()
        is not None
    )
    if not (is_patient or is_family_member):
        raise HTTPException(403, detail="Access denied")

    result = []
    for conn in (
        db.query(models.FamilyConnections)
        .filter(models.FamilyConnections.patient_id == patient_id)
        .all()
    ):
        perms = (
            db.query(models.FamilyPermissions)
            .filter(
                models.FamilyPermissions.patient_id == patient_id,
                models.FamilyPermissions.family_member_id
                == conn.family_member_id,
            )
            .first()
        )
        plist = perms.permissions if perms else []
        result.append(
            {
                "family_member_id": conn.family_member_id,
                "name": conn.family_member.name,
                "email": conn.family_member.email,
                "relationship_type": conn.relationship_type,
                "permissions": {
                    "can_view_records": "view_records" in plist,
                    "can_book_appointments": "book_appointments" in plist,
                    "can_message_doctor": "message_doctor" in plist,
                    "can_view_vitals": "view_vitals" in plist,
                    "can_manage_family": "manage_family" in plist,
                },
            }
        )
    return result


@router.put("/permissions/{patient_id}/{family_member_id}")
def update_family_permissions(
    patient_id: int,
    family_member_id: int,
    permission_update: schemas.FamilyPermissionUpdate,
    current_user=Depends(auth.check_patient),
    db: Session = Depends(get_db),
):
    if current_user.id != patient_id:
        raise HTTPException(403, detail="Only the patient can update permissions")

    conn = (
        db.query(models.FamilyConnections)
        .filter(
            models.FamilyConnections.patient_id == patient_id,
            models.FamilyConnections.family_member_id == family_member_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(404, detail="Family member not found")

    perms_record = (
        db.query(models.FamilyPermissions)
        .filter(
            models.FamilyPermissions.patient_id == patient_id,
            models.FamilyPermissions.family_member_id == family_member_id,
        )
        .first()
    )
    if not perms_record:
        perms_record = models.FamilyPermissions(
            patient_id=patient_id,
            family_member_id=family_member_id,
            permissions=[],
        )
        db.add(perms_record)

    cp = set(perms_record.permissions or [])
    for attr, key in [
        ("can_view_records", "view_records"),
        ("can_book_appointments", "book_appointments"),
        ("can_message_doctor", "message_doctor"),
        ("can_view_vitals", "view_vitals"),
        ("can_manage_family", "manage_family"),
    ]:
        val = getattr(permission_update, attr)
        if val is not None:
            cp.add(key) if val else cp.discard(key)
    perms_record.permissions = list(cp)

    if "message_doctor" in cp:
        for chat in (
            db.query(models.ChatRoom)
            .filter(models.ChatRoom.patient_id == patient_id)
            .all()
        ):
            if not (
                db.query(models.ChatParticipant)
                .filter(
                    models.ChatParticipant.chat_id == chat.id,
                    models.ChatParticipant.user_id == family_member_id,
                )
                .first()
            ):
                db.add(
                    models.ChatParticipant(
                        chat_id=chat.id, user_id=family_member_id
                    )
                )

    db.commit()
    db.refresh(perms_record)
    return {
        "message": "Permissions updated successfully",
        "patient_id": patient_id,
        "family_member_id": family_member_id,
        "permissions": {
            "can_view_records": "view_records" in cp,
            "can_book_appointments": "book_appointments" in cp,
            "can_message_doctor": "message_doctor" in cp,
            "can_view_vitals": "view_vitals" in cp,
            "can_manage_family": "manage_family" in cp,
        },
    }



@router.get("/permissions/check")
def check_family_permissions(
    patient_id: int, current_user=Depends(auth.check_family), db: Session = Depends(get_db)
):
    fc = (
        db.query(models.FamilyConnections)
        .filter(
            models.FamilyConnections.patient_id == patient_id,
            models.FamilyConnections.family_member_id == current_user.id,
        )
        .first()
    )
    if not fc:
        raise HTTPException(403, detail="No family relationship found")

    perms = (
        db.query(models.FamilyPermissions)
        .filter(
            models.FamilyPermissions.patient_id == patient_id,
            models.FamilyPermissions.family_member_id == current_user.id,
        )
        .first()
    )
    plist = perms.permissions if perms else []
    return {
        "patient_id": patient_id,
        "patient_name": fc.patient.name,
        "relationship_type": fc.relationship_type,
        "permissions": {
            "can_view_records": "view_records" in plist,
            "can_book_appointments": "book_appointments" in plist,
            "can_message_doctor": "message_doctor" in plist,
            "can_view_vitals": "view_vitals" in plist,
            "can_manage_family": "manage_family" in plist,
        },
    }


# Remaining endpoints (book-appointment, patient-appointments, vitals, etc.)
# must also filter permissions by both patient_id and family_member_id as shown above.


@router.get('/my-patients')
def get_my_patients(
    current_user = Depends(auth.check_family),
    db: Session = Depends(get_db)
):
    """Get all patients that this family member has access to"""
    
    family_connections = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.family_member_id == current_user.id
    ).all()
    
    result = []
    for connection in family_connections:
        patient = connection.patient
        
        # Get permissions
        permissions = db.query(models.FamilyPermissions).filter(
            models.FamilyPermissions.family_member_id == current_user.id
        ).first()
        
        permission_list = permissions.permissions if permissions else []
        
        result.append({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "patient_email": patient.email,
            "relationship_type": connection.relationship_type,
            "permissions": {
                "can_view_records": "view_records" in permission_list,
                "can_book_appointments": "book_appointments" in permission_list,
                "can_message_doctor": "message_doctor" in permission_list,
                "can_view_vitals": "view_vitals" in permission_list,
                "can_manage_family": "manage_family" in permission_list
            }
        })
    
    return result

@router.post('/book-appointment/{patient_id}')
def family_book_appointment(
    patient_id: int,
    appointment: schemas.BookAppointment,
    current_user = Depends(auth.check_family),
    db: Session = Depends(get_db)
):
    """Allow family member to book appointment for patient if they have permission"""
    
    # Check family relationship
    family_connection = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.patient_id == patient_id,
        models.FamilyConnections.family_member_id == current_user.id
    ).first()
    
    if not family_connection:
        raise HTTPException(status_code=403, detail="No family relationship found")
    
    # Check permissions
    permissions = db.query(models.FamilyPermissions).filter(
    models.FamilyPermissions.patient_id == patient_id,
    models.FamilyPermissions.family_member_id == current_user.id
        ).first()

    
    permission_list = permissions.permissions if permissions else []
    
    if "book_appointments" not in permission_list:
        raise HTTPException(status_code=403, detail="No permission to book appointments")
    
    # Book appointment for the patient
    return crud.book_appointment(db, appointment, patient_id)

@router.get('/patient-appointments/{patient_id}')
def get_patient_appointments_for_family(
    patient_id: int,
    current_user = Depends(auth.check_family),
    db: Session = Depends(get_db)
):
    """Get patient appointments if family member has view_records permission"""
    
    # Check family relationship
    family_connection = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.patient_id == patient_id,
        models.FamilyConnections.family_member_id == current_user.id
    ).first()
    
    if not family_connection:
        raise HTTPException(status_code=403, detail="No family relationship found")
    
    # Check permissions
    permissions = db.query(models.FamilyPermissions).filter(
    models.FamilyPermissions.patient_id == patient_id,
    models.FamilyPermissions.family_member_id == current_user.id
).first()

    
    permission_list = permissions.permissions if permissions else []
    
    if "view_records" not in permission_list:
        raise HTTPException(status_code=403, detail="No permission to view appointments")
    
    # Get appointments
    appointments = db.query(models.Appointments).filter(
        models.Appointments.patient_id == patient_id
    ).all()
    
    result = []
    for appointment in appointments:
        doctor_info = db.query(models.User).filter(models.User.id == appointment.doctor_id).first()
        
        result.append({
            "id": appointment.id,
            "doctor_id": appointment.doctor_id,
            "doctor_name": doctor_info.name if doctor_info else "Unknown Doctor",
            "appointment_date": appointment.date_time.isoformat(),
            "appointment_time": appointment.date_time.strftime("%I:%M %p"),
            "appointment_day": appointment.date_time.strftime("%A, %B %d, %Y"),
            "status": appointment.status.value,
            "status_display": appointment.status.value.title(),
            "can_cancel": False  # Family members typically can't cancel
        })
    
    return result

@router.get('/patient-vitals/{patient_id}')
def get_patient_vitals_for_family(
    patient_id: int,
    current_user = Depends(auth.check_family),
    db: Session = Depends(get_db)
):
    """Get patient vitals if family member has view_records permission"""
    
    # Check family relationship
    family_connection = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.patient_id == patient_id,
        models.FamilyConnections.family_member_id == current_user.id
    ).first()
    
    if not family_connection:
        raise HTTPException(status_code=403, detail="No family relationship found")
    
    # Check permissions - FIXED: Check for view_records instead of view_vitals
    permissions = db.query(models.FamilyPermissions).filter(
    models.FamilyPermissions.patient_id == patient_id,
    models.FamilyPermissions.family_member_id == current_user.id
).first()

    
    permission_list = permissions.permissions if permissions else []
    
    # CHANGED: "view_vitals" -> "view_records"
    if "view_records" not in permission_list:
        raise HTTPException(status_code=403, detail="No permission to view medical records")
    
    # Get patient
    patient = db.query(models.User).filter(models.User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return crud.get_vitals(patient)

@router.get("/patient-records/{patient_id}")
def get_patient_records_for_family(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.check_family)
):
    """
    Family members can fetch vitals for a patient if they have view_records permission.
    """
    # Verify family relationship
    fc = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.patient_id == patient_id,
        models.FamilyConnections.family_member_id == current_user.id
    ).first()
    if not fc:
        raise HTTPException(status_code=403, detail="No access to this patient")

    # Check view_records permission
    fp = db.query(models.FamilyPermissions).filter(
        models.FamilyPermissions.family_member_id == current_user.id
    ).first()
    if not fp or "view_records" not in fp.permissions:
        raise HTTPException(status_code=403, detail="No permission to view records")

    # Fetch vitals
    vitals = db.query(models.Vitals).filter(
        models.Vitals.patient_id == patient_id
    ).order_by(models.Vitals.timestamp.desc()).all()
    return vitals



# Helper function to check family permissions
def check_family_permission(patient_id: int, permission: str, family_member_id: int, db: Session):
    """Helper function to check if family member has specific permission for patient"""
    
    # Check family relationship
    family_connection = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.patient_id == patient_id,
        models.FamilyConnections.family_member_id == family_member_id
    ).first()
    
    if not family_connection:
        return False
    
    # Check permissions
    permissions = db.query(models.FamilyPermissions).filter(
        models.FamilyPermissions.family_member_id == family_member_id
    ).first()
    
    permission_list = permissions.permissions if permissions else []
    return permission in permission_list

@router.post('/add-family-to-chats/{patient_id}')
def add_family_to_patient_chats(
    patient_id: int,
    current_user = Depends(auth.check_family),
    db: Session = Depends(get_db)
):
    """Add family member to all chat rooms of a patient they have access to"""
    
    # Verify family connection
    family_connection = db.query(models.FamilyConnections).filter(
        models.FamilyConnections.patient_id == patient_id,
        models.FamilyConnections.family_member_id == current_user.id
    ).first()
    
    if not family_connection:
        raise HTTPException(status_code=403, detail="No family relationship found")
    
    # Check permissions
    permissions = db.query(models.FamilyPermissions).filter(
        models.FamilyPermissions.family_member_id == current_user.id
    ).first()
    
    permission_list = permissions.permissions if permissions else []
    
    if "message_doctor" not in permission_list:
        raise HTTPException(status_code=403, detail="No permission to message doctor")
    
    # Get all chat rooms for this patient
    patient_chats = db.query(models.ChatRoom).filter(
        models.ChatRoom.patient_id == patient_id
    ).all()
    
    if not patient_chats:
        # Fallback: find by participants
        patient_chats = (
            db.query(models.ChatRoom)
            .join(models.ChatParticipant, models.ChatParticipant.chat_id == models.ChatRoom.id)
            .filter(models.ChatParticipant.user_id == patient_id)
            .all()
        )
    
    added_count = 0
    for chat in patient_chats:
        existing_participant = db.query(models.ChatParticipant).filter(
            models.ChatParticipant.chat_id == chat.id,
            models.ChatParticipant.user_id == current_user.id
        ).first()
        
        if not existing_participant:
            new_participant = models.ChatParticipant(
                chat_id=chat.id,
                user_id=current_user.id
            )
            db.add(new_participant)
            added_count += 1
    
    db.commit()
    
    return {
        "message": f"Added to {added_count} chat rooms",
        "patient_id": patient_id,
        "added_to_chats": added_count
    }

    


         

