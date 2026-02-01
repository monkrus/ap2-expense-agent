import requests
r = requests.post('http://localhost:8000/api/v1/auth/login', json={'username': 'employee1', 'password': 'Password123!'})
if r.status_code == 200:
    print(r.json()['access_token'])
else:
    print(f"Error: {r.status_code}")
