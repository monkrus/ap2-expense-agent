# Default User Seeding System

## Overview

This application automatically seeds **4 default test users** every time the backend starts. These users will ALWAYS exist and will be created if they don't exist in the database.

## Default Users

The following users are **permanently configured** and cannot be changed:

| Username | Email | Password | Role |
|----------|-------|----------|------|
| `admintest` | admintest@example.com | `AgentTest!` | ADMIN |
| `testuser` | testuser@example.com | `AgentTest!` | MANAGER |
| `emptest` | emptest@example.com | `AgentTest!` | EMPLOYEE |
| `emptest2` | emptest2@example.com | `AgentTest!` | EMPLOYEE |

## How It Works

### Automatic Seeding on Startup

The seeding system runs automatically when the backend starts:

1. **On Backend Startup**: The `ensure_default_users_exist()` function runs
2. **Checks Existence**: It checks if each default user exists in the database
3. **Creates Missing Users**: Any missing users are automatically created
4. **Skips Existing Users**: If a user already exists, it's left unchanged

You'll see this message in the console:
```
[SEED] All 4 default users already exist
```
or
```
[SEED] Created 2 default users
```

### Location of Code

- **Seed Data**: `backend/src/seed_data.py` - Contains the DEFAULT_USERS list and seeding logic
- **API Integration**: `backend/src/api.py` - Calls `ensure_default_users_exist()` on startup
- **Setup Script**: `backend/scripts/setup_correct_users.py` - Manual setup script

## Manual Operations

### Verify Users Exist

```bash
cd backend
../.venv/Scripts/python.exe scripts/verify_users.py
```

### Recreate Users (Delete and Recreate)

```bash
cd backend
../.venv/Scripts/python.exe scripts/setup_correct_users.py
```

### Reset Passwords to Default

If you need to reset all default users' passwords back to `AgentTest!`:

```python
from src.database import SessionLocal
from src.seed_data import reset_default_users_passwords

db = SessionLocal()
try:
    reset_default_users_passwords(db)
finally:
    db.close()
```

## Modifying Default Users

**⚠️ IMPORTANT**: To change the default users (usernames, emails, passwords, or roles):

1. Edit `backend/src/seed_data.py`
2. Modify the `DEFAULT_USERS` list at the top of the file
3. Restart the backend - changes will take effect on next startup

```python
DEFAULT_USERS = [
    {
        "username": "admintest",
        "email": "admintest@example.com",
        "full_name": "Admin Test User",
        "role": UserRole.ADMIN,
        "password": "AgentTest!"
    },
    # ... add more users here
]
```

## Security Notes

- These are **TEST USERS ONLY** - not for production use
- All users share the same password: `AgentTest!`
- All users are active and verified by default
- All users have zero failed login attempts

## Database Reset

If you delete the database file (`backend/expenses.db`), these users will be automatically recreated when the backend starts.

## Testing

The seeding system ensures that you always have working test accounts for:
- Testing authentication
- Testing role-based permissions (admin, manager, employee)
- Testing multi-user scenarios
- Development and debugging
