from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Shared configuration across all microservices"""
    
    # Database URL - use PostgreSQL container
    DATABASE_URL: str = "postgresql://telehealth_user:telehealth_password@telehealth-postgres:5432/telehealth"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Service URLs (for inter-service communication)
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    PATIENT_SERVICE_URL: str = "http://patient-service:8000"
    DOCTOR_SERVICE_URL: str = "http://doctor-service:8000"
    APPOINTMENT_SERVICE_URL: str = "http://appointment-service:8000"
    FAMILY_SERVICE_URL: str = "http://family-service:8000"
    CHAT_SERVICE_URL: str = "http://chat-service:8000"
    ADMIN_SERVICE_URL: str = "http://admin-service:8000"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
