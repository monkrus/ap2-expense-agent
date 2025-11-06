import sys
sys.path.insert(0, '/home/user/ap2-expense-agent/backend')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api import app
from src.database import get_db, Base
from src.models import User
from datetime import datetime
from src.services.auth_service import AuthService

# Create test database
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Create a test user
db = TestingSessionLocal()
test_user = User(
    id="test-id",
    email="test@example.com",
    username="testuser",
    full_name="Test User",
    hashed_password=AuthService.hash_password("Password123!"),
    role="employee",
    is_active=True,
    is_verified=True,
    created_at=datetime.utcnow()
)
db.add(test_user)
db.commit()
db.close()

# Try to register with duplicate email
response = client.post(
    "/api/v1/auth/register",
    json={
        "email": "test@example.com",
        "username": "differentuser",
        "password": "Password123!",
        "full_name": "Different User",
        "role": "employee"
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response JSON: {response.json()}")
print(f"Response keys: {list(response.json().keys())}")
