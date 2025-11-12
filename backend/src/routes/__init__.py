from .admin import router as admin_router
from .auth import router as auth_router
from .oauth import router as oauth_router
from .users import router as users_router

__all__ = ["auth_router", "users_router", "oauth_router", "admin_router"]
