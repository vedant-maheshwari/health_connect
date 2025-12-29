import time
import urllib.request
import urllib.parse
import json
import ssl

BASE_URL = "http://localhost:8000"  # API Gateway
DOCTOR_EMAIL = "doctor@example.com"
DOCTOR_PASSWORD = "password"

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    
    # Check if data is already bytes (form data)
    if data and not isinstance(data, bytes) and headers.get('Content-Type') != 'application/x-www-form-urlencoded':
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif data and isinstance(data, str):
         data = data.encode('utf-8')

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read()
            duration = time.time() - start_time
            return duration, response.status, json.loads(body)
    except urllib.error.HTTPError as e:
        duration = time.time() - start_time
        return duration, e.code, json.loads(e.read())
    except Exception as e:
        print(f"Error: {e}")
        return 0, 0, None

def test_latency():
    print(f"Testing connectivity to {BASE_URL}...")

    # 0. Register Doctor (ensure account exists)
    reg_data = json.dumps({
        "name": "Test Doctor",
        "email": f"testdoc_{int(time.time())}@example.com", # unique email
        "password": "password",
        "date_of_birth": "1980-01-01",
        "medical_license": "TEST12345"
    }).encode('utf-8')

    duration, status, reg_res = make_request(
        f"{BASE_URL}/register/doctor",
        "POST",
        data=reg_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"Register Time: {duration:.4f}s (Status: {status})")
    
    if status not in [200, 201]:
        print(f"Registration failed: {status}")
        return

    # Use the new credentials
    username = reg_res["email"]
    
    # 1. Login
    form_data = urllib.parse.urlencode({
        "username": username,
        "password": "password"
    }).encode('utf-8')
    
    duration, status, data = make_request(
        f"{BASE_URL}/token", 
        "POST", 
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print(f"Login Time: {duration:.4f}s")
    
    if status != 200:
        print(f"Login failed: {status}")
        return
        
    token = data["access_token"]
    user_id = data.get("user_id") # safely get user_id
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get User Profile (/user/me)
    duration, status, _ = make_request(f"{BASE_URL}/user/me", headers=headers)
    print(f"/user/me Time: {duration:.4f}s (Status: {status})")

    # 3. Get Doctor Queue
    if user_id:
        duration, status, _ = make_request(f"{BASE_URL}/queue/doctor/{user_id}", headers=headers)
        print(f"/queue/doctor/{user_id} Time: {duration:.4f}s (Status: {status})")

    # 4. Get My Patients
    duration, status, _ = make_request(f"{BASE_URL}/doctors/me/patients", headers=headers)
    print(f"/doctors/me/patients Time: {duration:.4f}s (Status: {status})")

if __name__ == "__main__":
    test_latency()
