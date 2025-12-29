from sqlalchemy.orm import mapped_column, Mapped, relationship
from shared.database import Base
from sqlalchemy import String, ForeignKey, DateTime, Enum, JSON, UniqueConstraint, Text
from typing import List
import enum
from datetime import datetime, time


class UserRoles(str, enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"  
    FAMILY = "FAMILY"
    ADMIN = "ADMIN"

class RelationshipType(str, enum.Enum):
    SPOUSE = 'spouse'
    SIBLING = 'sibling'
    PARENT = 'parent'

class Status(str, enum.Enum):
    PENDING = 'pending'
    REJECTED = 'rejected'
    ACCECPTED = 'accepted'
    COMPLETED = 'completed'
    CANCELLED = "cancelled"



class User(Base):
    __tablename__ = 'users'

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    email : Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    hashed_password : Mapped[str] = mapped_column(String(100), nullable=False)
    role : Mapped[UserRoles] = mapped_column(Enum(UserRoles), nullable=False)
    date_of_birth : Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    medical_license : Mapped[str] = mapped_column(String(50),nullable=True)
    phone_number : Mapped[str] = mapped_column(String(15), nullable=True, index=True)  # For SMS

    family_connections: Mapped[List["FamilyConnections"]] = relationship(
        back_populates="patient",
        foreign_keys="FamilyConnections.patient_id",
        cascade="all, delete-orphan"
    )
    related_as_family: Mapped[List["FamilyConnections"]] = relationship(
        back_populates="family_member",
        foreign_keys="FamilyConnections.family_member_id",
        cascade="all, delete-orphan"
    )
    sent_invitations: Mapped[List["FamilyInvitations"]] = relationship(
        back_populates="invited",
        foreign_keys="FamilyInvitations.inviter_id",
        cascade="all, delete-orphan"
    )
    received_invitations: Mapped[List["FamilyInvitations"]] = relationship(
        back_populates="invitee",
        foreign_keys="FamilyInvitations.invitee_id",
        cascade="all, delete-orphan"
    )
    family_member_permissions: Mapped[List["FamilyPermissions"]] = relationship(
        back_populates="family_member",
        foreign_keys="FamilyPermissions.family_member_id",
        cascade="all, delete-orphan"
    )
    patient_permissions: Mapped[List["FamilyPermissions"]] = relationship(
        back_populates="patient",
        foreign_keys="FamilyPermissions.patient_id",
        cascade="all, delete-orphan"
    )
    patient_appointments: Mapped[List['Appointments']] = relationship(
        back_populates='patient',
        foreign_keys='Appointments.patient_id',
        cascade="all, delete-orphan"
    )
    doctor_appointments: Mapped[List['Appointments']] = relationship(
        back_populates='doctor',
        foreign_keys='Appointments.doctor_id',
        cascade="all, delete-orphan"
    )
    vitals: Mapped[List['Vitals']] = relationship(
        back_populates='patient',
        foreign_keys='Vitals.patient_id',
        cascade="all, delete-orphan"
    )
    doctor_for_patient: Mapped[List['Vitals']] = relationship(
        back_populates='doctor',
        foreign_keys='Vitals.doctor_id',
        cascade="all, delete-orphan"
    )
    availability_settings: Mapped[List["DoctorAvailability"]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan"
    )

    patient_permissions: Mapped[List["FamilyPermissions"]] = relationship(
        "FamilyPermissions",
        foreign_keys="FamilyPermissions.patient_id",  
        back_populates="patient",
        cascade="all, delete-orphan"
    )

    # Phase 3A Relationships
    assigned_patients_as_doctor: Mapped[List["DoctorPatientAssignment"]] = relationship(
        "DoctorPatientAssignment",
        foreign_keys="DoctorPatientAssignment.doctor_id",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )
    assigned_doctors_as_patient: Mapped[List["DoctorPatientAssignment"]] = relationship(
        "DoctorPatientAssignment",
        foreign_keys="DoctorPatientAssignment.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    medical_records: Mapped[List["PatientRecord"]] = relationship(
        "PatientRecord",
        foreign_keys="PatientRecord.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    vitals_logs: Mapped[List["VitalsLog"]] = relationship(
        "VitalsLog",
        foreign_keys="VitalsLog.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan"
    )

    family_member_permissions: Mapped[List["FamilyPermissions"]] = relationship(
        "FamilyPermissions",
        foreign_keys="FamilyPermissions.family_member_id",  
        back_populates="family_member",
        cascade="all, delete-orphan"
    )


# models.py - ADD CASCADE DELETES

# Update FamilyConnections model
class FamilyConnections(Base):
    __tablename__ = 'family_connections'

    id : Mapped[int] = mapped_column(primary_key=True)
    patient_id : Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    family_member_id : Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    relationship_type : Mapped[str] = mapped_column(Enum(RelationshipType), nullable=False)

    patient : Mapped["User"] = relationship(back_populates='family_connections', foreign_keys=[patient_id])
    family_member : Mapped['User'] = relationship(back_populates='related_as_family', foreign_keys=[family_member_id])

    __table_args__ = (
        UniqueConstraint('patient_id', 'family_member_id', name='unique_relationship'),
    )


# Update FamilyInvitations model
class FamilyInvitations(Base):
    __tablename__ = 'family_invitations'

    id : Mapped[int] = mapped_column(primary_key=True)
    inviter_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    invitee_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    relationship_type : Mapped[str] = mapped_column(Enum(RelationshipType), nullable=False)
    token : Mapped[str] = mapped_column(String)
    status : Mapped[str] = mapped_column(Enum(Status))

    invited : Mapped["User"] = relationship(back_populates='sent_invitations', foreign_keys=[inviter_id])
    invitee : Mapped["User"] = relationship(back_populates='received_invitations', foreign_keys=[invitee_id])


# Update FamilyPermissions model
class FamilyPermissions(Base):
    __tablename__ = 'family_permissions'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    family_member_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    permissions: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # FIXED: Explicit foreign_keys specification
    patient: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[patient_id],  
        back_populates="patient_permissions"
    )
    family_member: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[family_member_id],  
        back_populates="family_member_permissions"
    )
    
    __table_args__ = (
        UniqueConstraint('patient_id', 'family_member_id', name='unique_patient_family_permissions'),
    )


# Update Appointments model
class Appointments(Base):
    __tablename__ = 'appointments'

    id : Mapped[int] = mapped_column(primary_key=True)
    patient_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    doctor_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    date_time : Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    status : Mapped[str] = mapped_column(
        Enum(Status, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )

    patient : Mapped['User'] = relationship(back_populates='patient_appointments', foreign_keys=[patient_id])
    doctor : Mapped['User'] = relationship(back_populates='doctor_appointments', foreign_keys=[doctor_id])
    
    # New fields for robust integration
    severity: Mapped[int] = mapped_column(default=1) # 1-5 scale
    triage_id: Mapped[str] = mapped_column(nullable=True)
    delay_minutes: Mapped[int] = mapped_column(default=0)
    booking_source: Mapped[str] = mapped_column(String(20), default="web", nullable=True)  # web, sms, ai
    ai_notes: Mapped[str] = mapped_column(Text, nullable=True)  # AI analysis notes
    doctor_notes: Mapped[str] = mapped_column(Text, nullable=True)  # Doctor feedback
    
    # Queue relationship
    queue_entry: Mapped["AppointmentQueue"] = relationship("AppointmentQueue", back_populates="appointment", uselist=False)


# Update Vitals model
class Vitals(Base):
    __tablename__ = 'vitals'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    
    # Multiple vital measurements (all optional)
    bp: Mapped[int] = mapped_column(nullable=True)  # Systolic Blood Pressure
    heart_rate: Mapped[int] = mapped_column(nullable=True)  # BPM
    temperature: Mapped[float] = mapped_column(nullable=True)  # Fahrenheit
    notes: Mapped[str] = mapped_column(Text, nullable=True)  # Additional notes
    
    # Timestamp for when vitals were recorded
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped['User'] = relationship(back_populates='vitals', foreign_keys=[patient_id])
    doctor: Mapped['User'] = relationship(back_populates='doctor_for_patient', foreign_keys=[doctor_id])


# Update ChatParticipant model
class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    chat_room: Mapped["ChatRoom"] = relationship("ChatRoom", back_populates="participants")
    __table_args__ = (
        UniqueConstraint('chat_id', 'user_id', name='unique_chat_participant'),
    )


# Update ChatMessage model
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    chat_room: Mapped["ChatRoom"] = relationship("ChatRoom", back_populates="messages")
    # sender relationship optional:
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])


# Update DoctorAvailability model
class DoctorAvailability(Base):
    __tablename__ = 'doctor_availability'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column()  # 0-6 (Mon-Sun)
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()
    appointment_duration: Mapped[int] = mapped_column()  # minutes
    break_start: Mapped[time] = mapped_column(nullable=True)
    break_end: Mapped[time] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    
    doctor: Mapped["User"] = relationship(back_populates="availability_settings")

    
class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # ADD these missing fields:
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # ADD relationships:
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id])

    # Existing relationships
    participants: Mapped[List["ChatParticipant"]] = relationship("ChatParticipant", back_populates="chat_room", cascade="all, delete-orphan")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")


# ==========================================
# Phase 3A: Hospital Management System Models
# ==========================================

class DoctorPatientAssignment(Base):
    __tablename__ = 'doctor_patient_assignments'

    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_primary: Mapped[bool] = mapped_column(default=True)

    # Relationships
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id], back_populates="assigned_patients_as_doctor")
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id], back_populates="assigned_doctors_as_patient")


class PatientRecord(Base):
    """Electronic Medical Record (EMR) - Visit Notes"""
    __tablename__ = 'patient_records'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # SOAP Note Format
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=True)
    subjective: Mapped[str] = mapped_column(Text, nullable=True)  # History, Symptoms
    objective: Mapped[str] = mapped_column(Text, nullable=True)   # Exam findings, Vitals summary
    assessment: Mapped[str] = mapped_column(Text, nullable=True)  # Diagnosis
    plan: Mapped[str] = mapped_column(Text, nullable=True)        # Treatment, Prescriptions

    # Relationships
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id], back_populates="medical_records")
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id])


class VitalsLog(Base):
    """Detailed Vitals Tracking"""
    __tablename__ = 'vitals_log'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Vitals Data
    bp_systolic: Mapped[int] = mapped_column(nullable=True)
    bp_diastolic: Mapped[int] = mapped_column(nullable=True)
    heart_rate: Mapped[int] = mapped_column(nullable=True)      # BPM
    temperature: Mapped[float] = mapped_column(nullable=True)   # Fahrenheit/Celsius
    weight: Mapped[float] = mapped_column(nullable=True)        # kg
    oxygen_saturation: Mapped[int] = mapped_column(nullable=True) # %

    # Relationships
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id], back_populates="vitals_logs")
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id])


# ============================================================
# PHASE 3B: Queue Management & Notification Models
# ============================================================

class QueueStatus(str, enum.Enum):
    WAITING = 'WAITING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    DELAYED = 'DELAYED'
    NO_SHOW = 'NO_SHOW'
    REMOVED = 'REMOVED'


class AppointmentQueue(Base):
    """Real-time queue tracking for appointments"""
    __tablename__ = 'appointment_queue'

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey('appointments.id', ondelete="CASCADE"), unique=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)
    queue_position: Mapped[int] = mapped_column(default=0)
    estimated_wait_minutes: Mapped[int] = mapped_column(default=0)
    check_in_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[QueueStatus] = mapped_column(Enum(QueueStatus), default=QueueStatus.WAITING)
    delay_minutes: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    appointment: Mapped["Appointments"] = relationship("Appointments", back_populates="queue_entry")


class DoctorDelayStatus(Base):
    """Tracks current delay status for each doctor"""
    __tablename__ = 'doctor_delay_status'

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), unique=True, index=True)
    current_delay_minutes: Mapped[int] = mapped_column(default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reason: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationship
    doctor: Mapped["User"] = relationship("User")


class ReminderType(str, enum.Enum):
    FOLLOW_UP = 'follow_up'
    MEDICATION = 'medication'
    LAB_RESULT = 'lab_result'
    APPOINTMENT_24HR = 'appointment_24hr'
    APPOINTMENT_1HR = 'appointment_1hr'
    MISSED_APPOINTMENT = 'missed_appointment'


class Reminder(Base):
    """Patient reminders and notifications"""
    __tablename__ = 'reminders'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)
    type: Mapped[ReminderType] = mapped_column(Enum(ReminderType))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    sent: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    dismissed: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    related_id: Mapped[int] = mapped_column(nullable=True)  # appointment_id, prescription_id, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])


class MedicationFrequency(str, enum.Enum):
    ONCE_DAILY = 'once_daily'
    TWICE_DAILY = 'twice_daily'
    THREE_TIMES = 'three_times'
    WEEKLY = 'weekly'
    AS_NEEDED = 'as_needed'


class MedicationSchedule(Base):
    """Patient medication schedules for reminders"""
    __tablename__ = 'medication_schedules'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)
    medication_name: Mapped[str] = mapped_column(String(100))
    dosage: Mapped[str] = mapped_column(String(50))
    frequency: Mapped[MedicationFrequency] = mapped_column(Enum(MedicationFrequency))
    time_of_day: Mapped[str] = mapped_column(String(50), nullable=True)  # "morning", "8:00 AM, 8:00 PM"
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    prescribed_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    doctor: Mapped["User"] = relationship("User", foreign_keys=[prescribed_by])
