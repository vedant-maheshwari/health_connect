#!/bin/bash
# Test Patient Dashboard API

echo "Step 1: Login to get token"
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=vedant@test.com&password=password123" | jq -r '.access_token')

echo "Token: $TOKEN"
echo ""

echo "Step 2: Fetch appointments with AI details"
curl -s "http://localhost:8000/patient/appointments/detailed" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "Step 3: Filter to show only AI appointments"
curl -s "http://localhost:8000/patient/appointments/detailed" \
  -H "Authorization: Bearer $TOKEN" | jq '[.[] | select(.booking_source == "ai") | {id, doctor_name, status, booking_source, severity, ai_notes}]'
