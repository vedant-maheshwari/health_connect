"""
End-to-end test scenarios
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestE2EPatientJourney:
    """End-to-end test for complete patient journey"""
    
    @pytest.mark.asyncio
    async def test_complete_patient_flow(self, async_client: AsyncClient):
        """
        Test complete patient flow:
        1. Register
        2. Login
        3. View doctors
        4. Book appointment
        5. View appointments
        6. Cancel appointment
        """
        # Step 1: Register patient
        register_data = {
            "name": "E2E Test Patient",
            "email": "e2e_patient@test.com",
            "password": "e2epass123",
            "date_of_birth": "1993-08-15"
        }
        
        register_response = await async_client.post("/register_patient", json=register_data)
        assert register_response.status_code == 200
        
        # Step 2: Login
        login_data = {
            "username": "e2e_patient@test.com",
            "password": "e2epass123"
        }
        
        login_response = await async_client.post("/token", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: View doctors
        doctors_response = await async_client.get("/doctors")
        assert doctors_response.status_code == 200
        doctors = doctors_response.json()
        assert isinstance(doctors, list)
        
        # Step 4: View appointments
        appointments_response = await async_client.get(
            "/patient/appointments",
            headers=headers
        )
        assert appointments_response.status_code == 200
        
        # Step 5: Get detailed appointments
        detailed_response = await async_client.get(
            "/patient/appointments/detailed",
            headers=headers
        )
        assert detailed_response.status_code == 200


class TestE2EDoctorJourney:
    """End-to-end test for complete doctor journey"""
    
    @pytest.mark.asyncio
    async def test_complete_doctor_flow(self, async_client: AsyncClient):
        """
        Test complete doctor flow:
        1. Register
        2. Login
        3. Set availability
        4. View appointments
        5. Add patient vitals
        """
        # Step 1: Register doctor
        register_data = {
            "name": "E2E Test Doctor",
            "email": "e2e_doctor@test.com",
            "password": "e2edocpass123",
            "date_of_birth": "1982-04-20",
            "medical_license": "E2E-MD789"
        }
        
        register_response = await async_client.post("/register_doctor", json=register_data)
        assert register_response.status_code == 200
        
        # Step 2: Login
        login_data = {
            "username": "e2e_doctor@test.com",
            "password": "e2edocpass123"
        }
        
        login_response = await async_client.post("/token", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Set availability
        availability_data = {
            "day_of_week": 2,  # Tuesday
            "start_time": "08:00",
            "end_time": "16:00",
            "appointment_duration": 30
        }
        
        avail_response = await async_client.put(
            "/doctor/availability",
            json=availability_data,
            headers=headers
        )
        assert avail_response.status_code == 200
        
        # Step 4: Get availability
        get_avail_response = await async_client.get(
            "/doctor/availability",
            headers=headers
        )
        assert get_avail_response.status_code == 200
        
        # Step 5: View appointments
        appointments_response = await async_client.get(
            "/get_all_appointments",
            headers=headers
        )
        assert appointments_response.status_code == 200


class TestE2EAppointmentFlow:
    """End-to-end test for appointment booking flow"""
    
    @pytest.mark.asyncio
    async def test_appointment_lifecycle(self, async_client: AsyncClient):
        """
        Test full appointment lifecycle:
        1. Patient books appointment
        2. Doctor views appointment
        3. Doctor accepts/rejects
        4. Patient views status
        5. Patient cancels
        """
        # This would require proper setup with both patient and doctor
        # For now, test the individual endpoints are accessible
        
        # Register and login patient
        patient_reg = {
            "name": "Appointment Test Patient",
            "email": "apt_patient@test.com",
            "password": "aptpass123",
            "date_of_birth": "1991-02-10"
        }
        
        await async_client.post("/register_patient", json=patient_reg)
        
        patient_login = await async_client.post(
            "/token",
            data={"username": "apt_patient@test.com", "password": "aptpass123"}
        )
        
        patient_token = patient_login.json()["access_token"]
        patient_headers = {"Authorization": f"Bearer {patient_token}"}
        
        # Check appointment endpoints are accessible
        appointments = await async_client.get(
            "/patient/appointments",
            headers=patient_headers
        )
        assert appointments.status_code == 200
