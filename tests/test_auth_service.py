"""
Unit tests for Authentication Service
"""
import pytest
from httpx import AsyncClient
from datetime import datetime


class TestAuthService:
    """Test suite for authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_patient_success(self, async_client: AsyncClient):
        """Test successful patient registration"""
        payload = {
            "name": "New Patient",
            "email": "newpatient@test.com",
            "password": "securepass123",
            "date_of_birth": "1995-05-15"
        }
        
        response = await async_client.post("/register_patient", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == payload["email"]
        assert data["name"] == payload["name"]
        assert data["role"] == "patient"
        assert "id" in data
    
    
    @pytest.mark.asyncio
    async def test_register_patient_duplicate_email(self, async_client: AsyncClient):
        """Test registration with duplicate email fails"""
        payload = {
            "name": "Test User",
            "email": "patient@test.com",  # Already exists in fixtures
            "password": "pass123",
            "date_of_birth": "1990-01-01"
        }
        
        response = await async_client.post("/register_patient", json=payload)
        assert response.status_code in [400, 409]  # Bad request or conflict
    
    
    @pytest.mark.asyncio
    async def test_register_doctor_success(self, async_client: AsyncClient):
        """Test successful doctor registration"""
        payload = {
            "name": "New Doctor",
            "email": "newdoctor@test.com",
            "password": "docpass123",
            "date_of_birth": "1980-03-20",
            "medical_license": "MD67890"
        }
        
        response = await async_client.post("/register_doctor", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == payload["email"]
        assert data["role"] == "doctor"
        assert data["medical_license"] == payload["medical_license"]
    
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient):
        """Test successful login"""
        # First register a user
        register_payload = {
            "name": "Login Test User",
            "email": "logintest@test.com",
            "password": "testpass123",
            "date_of_birth": "1992-06-10"
        }
        await async_client.post("/register_patient", json=register_payload)
        
        # Now try to login
        login_data = {
            "username": "logintest@test.com",
            "password": "testpass123"
        }
        
        response = await async_client.post("/token", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Test login with invalid credentials fails"""
        login_data = {
            "username": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        
        response = await async_client.post("/token", data=login_data)
        assert response.status_code == 401
    
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, async_client: AsyncClient, patient_token: str):
        """Test getting current user info"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        response = await async_client.get("/user/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "role" in data
    
    
    @pytest.mark.asyncio
    async def test_ws_token_generation(self, async_client: AsyncClient, patient_token: str):
        """Test WebSocket token generation"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        response = await async_client.post("/ws-token", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "ws_token" in data
        assert len(data["ws_token"]) > 0
