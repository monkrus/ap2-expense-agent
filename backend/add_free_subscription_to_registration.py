#!/usr/bin/env python3
"""
Add automatic Free subscription creation when users register
This fixes usage tracking for Free tier users
"""

file_path = "src/routes/auth.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Add SubscriptionService and SubscriptionTier imports
old_imports = """from ..auth import AuthService, TOTPService, get_current_active_user, require_admin
from ..database import get_db
from ..email_service import EmailService
from ..models import PasswordResetToken, User, UserRole
from ..rate_limit import RateLimits, limiter"""

new_imports = """from ..auth import AuthService, TOTPService, get_current_active_user, require_admin
from ..database import get_db
from ..email_service import EmailService
from ..models import PasswordResetToken, User, UserRole, SubscriptionTier
from ..rate_limit import RateLimits, limiter
from ..billing import SubscriptionService"""

content = content.replace(old_imports, new_imports)

# Step 2: Add Free subscription creation after user is created
old_registration_code = """    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=user.id,
        request=request,
    )

    return user"""

new_registration_code = """    # Create Free tier subscription automatically for new users
    subscription_service = SubscriptionService(db)
    try:
        subscription_service.create_subscription(
            user_id=user.id,
            tier=SubscriptionTier.FREE,
            trial_days=0  # No trial for Free tier
        )
    except Exception as e:
        # Log but don't fail registration if subscription creation fails
        print(f"Warning: Failed to create Free subscription for user {user.id}: {e}")

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=user.id,
        request=request,
    )

    return user"""

content = content.replace(old_registration_code, new_registration_code)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE: Added automatic Free subscription creation to registration")
print("  - Added SubscriptionService and SubscriptionTier imports")
print("  - Added Free subscription creation after user registration")
print("  - All new users will now get a Free subscription automatically")
