from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import uuid
from typing import Optional
import httpx
import os

from ..database import get_db
from ..models import User, UserRole
from ..schemas import OAuth2AuthorizeRequest, OAuth2TokenRequest, OAuth2TokenResponse
from ..auth import AuthService, get_current_active_user
from ..config import settings

router = APIRouter(prefix="/api/v1/oauth2", tags=["OAuth2"])

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", settings.google_api_key or "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# In-memory storage for OAuth2 authorization codes (use Redis in production)
authorization_codes = {}
oauth_clients = {}

# Register some default OAuth2 clients (in production, store in database)
def init_oauth_clients():
    """Initialize default OAuth2 clients"""
    oauth_clients["ap2-expense-web"] = {
        "client_id": "ap2-expense-web",
        "client_secret": "dev-secret-change-in-production",
        "redirect_uris": [
            "http://localhost:3000/auth/callback",
            "http://localhost:5173/auth/callback"
        ],
        "grant_types": ["authorization_code", "refresh_token"],
        "scope": "read write"
    }

init_oauth_clients()

@router.get("/authorize")
async def authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: Optional[str] = "read",
    state: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """OAuth2 authorization endpoint"""
    # Validate client
    client = oauth_clients.get(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_id"
        )

    # Validate redirect URI
    if redirect_uri not in client["redirect_uris"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect_uri"
        )

    # Validate response type
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only 'code' response_type is supported"
        )

    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    authorization_codes[auth_code] = {
        "user_id": current_user.id,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }

    # Redirect back to client with authorization code
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"

    return RedirectResponse(url=redirect_url)

@router.post("/authorize", response_model=dict)
async def authorize_post(
    auth_request: OAuth2AuthorizeRequest,
    current_user: User = Depends(get_current_active_user)
):
    """OAuth2 authorization endpoint (POST)"""
    # Validate client
    client = oauth_clients.get(auth_request.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_id"
        )

    # Validate redirect URI
    if auth_request.redirect_uri not in client["redirect_uris"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect_uri"
        )

    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    authorization_codes[auth_code] = {
        "user_id": current_user.id,
        "client_id": auth_request.client_id,
        "redirect_uri": auth_request.redirect_uri,
        "scope": auth_request.scope,
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }

    return {
        "code": auth_code,
        "state": auth_request.state
    }

@router.post("/token", response_model=OAuth2TokenResponse)
async def token(
    token_request: OAuth2TokenRequest,
    db: Session = Depends(get_db)
):
    """OAuth2 token endpoint"""
    # Validate client
    client = oauth_clients.get(token_request.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_id"
        )

    # Validate client secret
    if client["client_secret"] != token_request.client_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client_secret"
        )

    if token_request.grant_type == "authorization_code":
        # Validate authorization code
        auth_code_data = authorization_codes.get(token_request.code)
        if not auth_code_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authorization code"
            )

        # Check if code is expired
        if auth_code_data["expires_at"] < datetime.utcnow():
            del authorization_codes[token_request.code]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code expired"
            )

        # Validate redirect URI
        if token_request.redirect_uri != auth_code_data["redirect_uri"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid redirect_uri"
            )

        # Get user
        user = db.query(User).filter(User.id == auth_code_data["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )

        # Generate tokens
        access_token = AuthService.create_access_token(
            data={"sub": user.id, "username": user.username, "role": user.role.value}
        )
        refresh_token = AuthService.create_refresh_token(user_id=user.id, db=db)

        # Delete used authorization code
        del authorization_codes[token_request.code]

        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=3600,
            refresh_token=refresh_token,
            scope=auth_code_data["scope"]
        )

    elif token_request.grant_type == "refresh_token":
        # Validate refresh token
        refresh_token_obj = AuthService.verify_refresh_token(token_request.refresh_token, db)

        # Get user
        user = db.query(User).filter(User.id == refresh_token_obj.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )

        # Generate new access token
        access_token = AuthService.create_access_token(
            data={"sub": user.id, "username": user.username, "role": user.role.value}
        )

        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=3600,
            scope="read write"
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant_type: {token_request.grant_type}"
        )

@router.get("/consent")
async def consent_page(
    client_id: str,
    redirect_uri: str,
    scope: str = "read",
    state: Optional[str] = None
):
    """OAuth2 consent page"""
    client = oauth_clients.get(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_id"
        )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorization Required</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: 50px auto;
                padding: 20px;
            }}
            .consent-box {{
                border: 1px solid #ddd;
                padding: 30px;
                border-radius: 8px;
                background: #f9f9f9;
            }}
            h2 {{
                color: #333;
            }}
            .permissions {{
                margin: 20px 0;
                padding: 15px;
                background: white;
                border-radius: 4px;
            }}
            .button {{
                padding: 10px 20px;
                margin: 5px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }}
            .approve {{
                background: #4CAF50;
                color: white;
            }}
            .deny {{
                background: #f44336;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="consent-box">
            <h2>Authorization Request</h2>
            <p><strong>{client_id}</strong> is requesting access to your account.</p>

            <div class="permissions">
                <h3>Requested Permissions:</h3>
                <ul>
                    <li>Read your profile information</li>
                    <li>Access expense data</li>
                    {'<li>Create and modify expenses</li>' if 'write' in scope else ''}
                </ul>
            </div>

            <form action="/api/v1/oauth2/authorize" method="GET">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="response_type" value="code">
                <input type="hidden" name="scope" value="{scope}">
                {f'<input type="hidden" name="state" value="{state}">' if state else ''}

                <button type="submit" class="button approve">Approve</button>
                <button type="button" class="button deny" onclick="window.location.href='{redirect_uri}?error=access_denied'">Deny</button>
            </form>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ============================================================================
# GOOGLE OAUTH 2.0 INTEGRATION
# ============================================================================

@router.get("/google/login")
async def google_login(state: Optional[str] = None):
    """Initiate Google OAuth login"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    # Build authorization URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }

    if state:
        params["state"] = state

    auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code for tokens"
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user information from Google"
            )

        google_user = userinfo_response.json()

    # Check if user exists
    user = db.query(User).filter(User.email == google_user["email"]).first()

    if not user:
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            email=google_user["email"],
            username=google_user["email"].split("@")[0] + "_" + str(uuid.uuid4())[:8],
            full_name=google_user.get("name", ""),
            hashed_password=AuthService.hash_password(secrets.token_urlsafe(24)),  # Random password (24 chars for bcrypt)
            role=UserRole.EMPLOYEE,
            is_active=True,
            is_verified=True  # Google accounts are pre-verified
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    app_access_token = AuthService.create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value}
    )
    refresh_token = AuthService.create_refresh_token(user_id=user.id, db=db)

    # Redirect to frontend with tokens
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    redirect_url = f"{frontend_url}/auth/google/success?access_token={app_access_token}&refresh_token={refresh_token}"

    if state:
        redirect_url += f"&state={state}"

    return RedirectResponse(url=redirect_url)


@router.post("/google/token")
async def google_token_exchange(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Exchange Google authorization code for app tokens (for mobile/SPA)
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )

    # Exchange code for Google tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user information"
            )

        google_user = userinfo_response.json()

    # Find or create user
    user = db.query(User).filter(User.email == google_user["email"]).first()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=google_user["email"],
            username=google_user["email"].split("@")[0] + "_" + str(uuid.uuid4())[:8],
            full_name=google_user.get("name", ""),
            hashed_password=AuthService.hash_password(secrets.token_urlsafe(24)),  # Random password (24 chars for bcrypt)
            role=UserRole.EMPLOYEE,
            is_active=True,
            is_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user.last_login = datetime.utcnow()
    db.commit()

    # Create app tokens
    app_access_token = AuthService.create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value}
    )
    refresh_token = AuthService.create_refresh_token(user_id=user.id, db=db)

    return {
        "access_token": app_access_token,
        "refresh_token": refresh_token,
        "expires_in": 3600,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value
        }
    }
