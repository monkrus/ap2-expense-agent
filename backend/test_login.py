import requests

# Test all users with AgentTest!
users = ['admintest', 'testuser', 'emptest', 'employee2']
password = 'AgentTest!'

print(f"Testing login with password: {password}")
print("=" * 50)

for username in users:
    response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={'username': username, 'password': password}
    )
    
    if response.status_code == 200:
        role = response.json().get('user', {}).get('role', 'unknown')
        print(f'{username:15} SUCCESS (role: {role})')
    else:
        error = response.json().get('error', {}).get('message', 'Unknown error')
        print(f'{username:15} FAILED - {error}')

print("=" * 50)
