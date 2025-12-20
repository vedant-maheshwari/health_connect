"""
Integration tests for Doctor Service
"""
import pytest
from httpx import AsyncClient


class TestDoctorService:
    """Test suite for doctor-related endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_all_doctors(self, async_client: AsyncClient):
        """Test getting list of all doctors"""
        response = await async_client.get("/doctors")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    
    @pytest.mark.asyncio
    async def test_get_all_doctors_alias(self, async_client: AsyncClient):
        """Test /all_doctors alias endpoint"""
        response = await async_client.get("/all_doctors")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    
    @pytest.mark.asyncio
    async def test_get_doctor_availability(self, async_client: AsyncClient, doctor_token: str):
        """Test getting doctor availability"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        response = await async_client.get("/doctor/availability", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "availabilities" in data or isinstance(data, list)
    
    
    @pytest.mark.asyncio
    async def test_set_doctor_availability(self, async_client: AsyncClient, doctor_token: str):
        """Test setting doctor availability"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        availability_data = {
            "day_of_week": 1,  # Monday
            "start_time": "09:00",
            "end_time": "17:00",
            "appointment_duration": 30,
            "break_start": "12:00",
            "break_end": "13:00"
        }
        
        response = await async_client.put(
            "/doctor/availability",
            json=availability_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "id" in data
    
    
    @pytest.mark.asyncio
    async def test_add_vital_signs(self, async_client: AsyncClient, doctor_token: str):
        """Test doctor adding patient vital signs"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        vital_data = {
            "patient_email": "patient@test.com",
            "bp": "120/80",
            "heart_rate": 72,
            "temperature": 98.6,
            "notes": "Normal vital signs"
        }
        
        response = await async_client.post(
            "/add_vital",
            json=vital_data,
            headers=headers
        )
        
        assert response.status_code in [200, 404]  # Success or patient not found
        
        if response.status_code == 200:
            data = response.json()
            assert "vital_id" in data or "message" in data
    
    
    @pytest.mark.asyncio
    async def test_unauthorized_add_vital(self, async_client: AsyncClient, patient_token: str):
        """Test that non-doctor cannot add vitals"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        vital_data = {
            "patient_email": "patient@test.com",
            "bp": "120/80",
            "heart_rate": 72,
            "temperature": 98.6,
            "notes": "Should fail"
        }
        
        response = await async_client.post(
            "/add_vital",
            json=vital_data,
            headers=headers
        )
        
        assert response.status_code == 403  # Forbidden
