from shared import models, schemas
from sqlalchemy.orm import Session
import uuid

def send_invitation(db : Session, inviter_id : int,  invitee_email : str, relationship_type : str):
    invitee = db.query(models.User).filter(models.User.email == invitee_email).first()
    if not invitee:
        return None
    
    token = str(uuid.uuid4())

    invitation = models.FamilyInvitations(
        inviter_id = inviter_id,
        invitee_id = invitee.id,
        relationship_type = relationship_type,
        token = token,
        status = models.Status.PENDING
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def respond_invitation(db : Session, token : str, action : str):
    invitation = db.query(models.FamilyInvitations).filter(models.FamilyInvitations.token == token).first()

    if not invitation:
        return None
    
    if action.lower() == 'accept':
        invitation.status = models.Status.ACCECPTED
        add_family_connection(db, invitation.inviter_id, invitation.invitee_id, invitation.relationship_type)
       

    else :
        invitation.status = models.Status.REJECTED
        db.commit()
        
    return invitation


        
def add_family_connection(db : Session, patient_id : int, family_member_id : int, relationship_type : str):
    connection = models.FamilyConnections(
        patient_id = patient_id,
        family_member_id = family_member_id,
        relationship_type = relationship_type
    )

    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection



