import requests
import json

url = "http://localhost:8000/api/v1/auth/login"

payload = {"username": "employee1", "password": "Password123!"}

print("Testing login...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

response = requests.post(url, json=payload)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"\nSuccess! Token: {data.get('access_token', '')[:50]}...")
else:
    print(f"\nFailed!")
