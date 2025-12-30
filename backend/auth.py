import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import RedirectResponse

from db import find_user_by_email, Collections
from logger.custom_logger import CustomLogger

_LOG = CustomLogger().get_logger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv("OAUTH_JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
OAUTH_CALLBACK_URL = os.getenv("OAUTH_CALLBACK_URL", "http://localhost:8000/auth/google/callback")

# Security scheme for FastAPI
security = HTTPBearer()

# OAuth client
oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


def create_jwt_token(user_data: dict) -> str:
    """Create JWT token with user information."""
    payload = {
        "sub": user_data["_id"],  # subject (user ID)
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "role": user_data.get("role", "individual"),
        "team_id": user_data.get("team_id"),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    # Get fresh user data from database
    user = await find_user_by_email(payload.get("email"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def ensure_role(allowed_roles: List[str]):
    """Dependency factory to ensure user has required role."""
    async def check_role(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "individual")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {allowed_roles}, current: {user_role}"
            )
        return current_user
    
    return check_role


# OAuth Routes
async def login_redirect(request: Request) -> RedirectResponse:
    """Redirect to Google OAuth login."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured"
        )
    
    redirect_uri = OAUTH_CALLBACK_URL
    return await oauth.google.authorize_redirect(request, redirect_uri)


async def google_callback(request: Request) -> RedirectResponse:
    """Handle Google OAuth callback."""
    try:
        # Get token from Google
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google"
            )
        
        email = user_info.get('email')
        name = user_info.get('name', '')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        # Find or create user
        user = await find_user_by_email(email)
        
        if not user:
            # Create new user with default role
            users = await Collections.users()
            user_doc = {
                "email": email,
                "name": name,
                "role": "individual",  # Default role
                "team_id": None,
                "bio": "",
                "strengths": [],
                "focus": [],
                "tags": [],
                "availability": [],
                "consent": {
                    "mentorship_matching": True,
                    "team_analytics": True,
                    "data_processing": True
                },
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow()
            }
            
            result = await users.insert_one(user_doc)
            user_doc["_id"] = str(result.inserted_id)
            user = user_doc
            
            _LOG.info("New user created via OAuth", email=email, user_id=str(result.inserted_id))
        else:
            # Update last login
            users = await Collections.users()
            await users.update_one(
                {"_id": user["_id"]}, 
                {"$set": {"last_login": datetime.utcnow()}}
            )
            _LOG.info("User logged in via OAuth", email=email, user_id=str(user["_id"]))
        
        # Create JWT token
        jwt_token = create_jwt_token(user)
        
        # Redirect to frontend with token
        frontend_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}"
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        _LOG.error("OAuth callback error", error=str(e))
        error_url = f"{FRONTEND_URL}/auth/error?error=oauth_failed"
        return RedirectResponse(url=error_url)


async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current user information."""
    # Remove sensitive fields
    safe_user = {
        "user_id": str(current_user["_id"]),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "role": current_user.get("role"),
        "team_id": current_user.get("team_id"),
        "bio": current_user.get("bio", ""),
        "strengths": current_user.get("strengths", []),
        "focus": current_user.get("focus", []),
        "tags": current_user.get("tags", []),
        "availability": current_user.get("availability", [])
    }
    
    return safe_user


# Role-based dependencies (shortcuts)
individual_required = ensure_role(["individual", "mentor", "counselor", "coordinator"])
mentor_required = ensure_role(["mentor", "counselor", "coordinator"])
counselor_required = ensure_role(["counselor", "coordinator"])
coordinator_required = ensure_role(["coordinator"])


# Utility functions
def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token without full validation."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        return payload.get("sub")
    except Exception:
        return None


async def update_user_profile(user_id: str, updates: dict) -> dict:
    """Update user profile information."""
    users = await Collections.users()
    
    # Only allow certain fields to be updated
    allowed_fields = ["name", "bio", "strengths", "focus", "tags", "availability", "consent"]
    safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if safe_updates:
        safe_updates["updated_at"] = datetime.utcnow()
        await users.update_one({"_id": user_id}, {"$set": safe_updates})
    
    return await users.find_one({"_id": user_id})


def validate_team_access(user: dict, target_team_id: str) -> bool:
    """Validate if user can access team data."""
    user_role = user.get("role", "individual")
    user_team = user.get("team_id")
    
    # Coordinators can access any team
    if user_role == "coordinator":
        return True
    
    # Others can only access their own team
    return user_team == target_team_id