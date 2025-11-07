import requests
import json

# Test admin login
resp = requests.post('http://localhost:8000/api/v1/auth/login', json={'username': 'admintest', 'password': 'AgentTest!'})
print(f"Admin Login Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✓ Login successful!")
    print(f"  User: {data.get('user', {}).get('username')}")
    print(f"  Role: {data.get('user', {}).get('role')}")
    print(f"  Token: {data.get('access_token')[:50]}...")
else:
    print(f"✗ Login failed: {resp.json()}")
