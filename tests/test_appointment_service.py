"""
Integration tests for Appointment Service
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestAppointmentService:
    """Test suite for appointment management"""
    
    @pytest.mark.asyncio
    async def test_get_available_appointments(self, async_client: AsyncClient):
        """Test getting available appointment slots"""
        doctor_id = 2  # Test doctor
        app_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = await async_client.get(
            f"/available_appointment?doctor_id={doctor_id}&app_date={app_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    
    @pytest.mark.asyncio
    async def test_create_appointment(self, async_client: AsyncClient, patient_token: str):
        """Test creating a new appointment"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        appointment_data = {
            "doctor_id": 2,
            "date_time": (datetime.now() + timedelta(days=2)).isoformat()
        }
        
        response = await async_client.post(
            "/create_appointment",
            json=appointment_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "appointment_id" in data or "message" in data
    
    
    @pytest.mark.asyncio
    async def test_get_all_appointments_doctor(self, async_client: AsyncClient, doctor_token: str):
        """Test doctor getting all their appointments"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        response = await async_client.get("/get_all_appointments", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check calendar format
        if len(data) > 0:
            assert "id" in data[0]
            assert "title" in data[0]
            assert "start" in data[0]
            assert "end" in data[0]
            assert "status" in data[0]
    
    
    @pytest.mark.asyncio
    async def test_reserve_slot(self, async_client: AsyncClient, patient_token: str):
        """Test reserving an appointment slot"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        reservation_data = {
            "doctor_id": 2,
            "slot_time": (datetime.now() + timedelta(days=3, hours=10)).isoformat()
        }
        
        response = await async_client.post(
            "/reserve_slot",
            json=reservation_data,
            headers=headers
        )
        
        # May succeed or fail depending on availability
        assert response.status_code in [200, 400, 409]
    
    
    @pytest.mark.asyncio
    async def test_appointment_response(self, async_client: AsyncClient, doctor_token: str):
        """Test doctor responding to appointment"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        # First create an appointment (would need to be set up properly)
        response_data = {
            "appointment_id": 1,
            "status": "accept"
        }
        
        response = await async_client.put(
            "/appointment_response",
            json=response_data,
            headers=headers
        )
        
        # May fail if appointment doesn't exist
        assert response.status_code in [200, 404]
    
    
    @pytest.mark.asyncio
    async def test_cancel_slot(self, async_client: AsyncClient, patient_token: str):
        """Test canceling an appointment slot"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        cancel_data = {"appointment_id": 1}
        
        response = await async_client.post(
            "/cancel_slot",
            json=cancel_data,
            headers=headers
        )
        
        # May fail if appointment doesn't exist or not authorized
        assert response.status_code in [200, 403, 404]


class TestPatientAppointments:
    """Test suite for patient appointment management"""
    
    @pytest.mark.asyncio
    async def test_get_patient_appointments(self, async_client: AsyncClient, patient_token: str):
        """Test getting patient's appointments"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        response = await async_client.get("/patient/appointments", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    
    @pytest.mark.asyncio
    async def test_get_patient_appointments_detailed(self, async_client: AsyncClient, patient_token: str):
        """Test getting detailed patient appointments"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        response = await async_client.get("/patient/appointments/detailed", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check detailed format
        if len(data) > 0:
            assert "doctor_name" in data[0]
            assert "appointment_date" in data[0]
            assert "status" in data[0]
    
    
    @pytest.mark.asyncio
    async def test_cancel_patient_appointment(self, async_client: AsyncClient, patient_token: str):
        """Test patient canceling their appointment"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        # Try to cancel appointment with ID 1
        response = await async_client.put(
            "/patient/appointments/1/cancel",
            headers=headers
        )
        
        # May succeed or fail depending on appointment existence
        assert response.status_code in [200, 400, 404]
    
    
    @pytest.mark.asyncio
    async def test_reschedule_appointment(self, async_client: AsyncClient, patient_token: str):
        """Test rescheduling an appointment"""
        headers = {"Authorization": f"Bearer {patient_token}"}
        
        reschedule_data = {
            "new_datetime": (datetime.now() + timedelta(days=5)).isoformat()
        }
        
        response = await async_client.post(
            "/patient/appointments/1/reschedule",
            json=reschedule_data,
            headers=headers
        )
        
        assert response.status_code in [200, 404]
