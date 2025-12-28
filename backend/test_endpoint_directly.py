"""Test the endpoint by directly calling the function"""
import asyncio
from unittest.mock import Mock
from src.routes.expenses import list_expenses
from src.database import SessionLocal
from src.models import User

# Create mock request
class MockRequest:
    headers = {"X-Organization-Id": "bd5fb358-d354-4089-a9b6-531e43b77540"}

# Get admin user
db = SessionLocal()
admin = db.query(User).filter(User.role == 'admin').first()

# Call the function directly
async def test():
    result = await list_expenses(
        request=MockRequest(),
        status_filter="pending",
        current_user=admin,
        db=db
    )

    print("Result type:", type(result))
    print("Result:", result if not isinstance(result, dict) else f"Dict with keys: {list(result.keys())}")

    if isinstance(result, dict):
        if 'expenses' in result:
            print(f"✓ Correct format! Contains 'expenses' key with {len(result['expenses'])} items")
        else:
            print(f"✗ Wrong format! Dict but no 'expenses' key. Keys: {list(result.keys())}")
    else:
        print(f"✗ Wrong format! Not a dict, it's a {type(result).__name__}")

asyncio.run(test())
