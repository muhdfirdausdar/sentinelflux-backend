"""
Authentication Routes for SentinelFlux API

This module provides authentication endpoints including JWT token generation.
The /auth/token endpoint is the ONLY endpoint that uses the old API key method.
All other endpoints should use JWT tokens for authentication.
"""

from fastapi import APIRouter, HTTPException, Security, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import timedelta, datetime, timezone
import uuid
from utils.async_log import get_logger
from utils.jwt_auth import jwt_manager, create_session_token, get_token_expiration_info, get_current_user_jwt
from utils.auth import get_current_user_with_legacy  # This allows legacy API key for token generation

logger = get_logger("auth_routes")

router = APIRouter()

# Request/Response models
class TokenResponse(BaseModel):
    """Response model for token generation"""
    access_token: str
    token_type: str
    expires_in_minutes: int
    expires_at: str
    client_id: str

class TokenInfoResponse(BaseModel):
    """Response model for token information"""
    valid: bool
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None
    expires_in_minutes: Optional[int] = None
    client_id: Optional[str] = None
    token_type: Optional[str] = None
    error: Optional[str] = None

@router.post("/token", response_model=TokenResponse)
async def generate_jwt_token(
    current_user = Security(get_current_user_with_legacy)  # This endpoint allows legacy API key authentication
):
    """
    Generate a JWT session token using API key authentication
    
    This is the ONLY endpoint that accepts legacy X-API-Key authentication.
    Once you get a JWT token from this endpoint, use it for all other API calls.
    
    Headers Required:
        X-API-Key: Your SentinelFlux API key (legacy authentication)
        OR
        Authorization: Bearer <existing-jwt-token> (if refreshing)
    
    Request Body: None required (empty body)
    
    The server automatically:
        - Generates a unique client ID (UUID)
        - Sets appropriate expiration (60 minutes)
        - Creates a secure JWT token
    
    Returns:
        JWT token that can be used for subsequent API calls
    """
    try:
        # Check authentication method used
        auth_method = current_user.get("auth_method", "unknown")
        
        if auth_method == "api_key":
            # Generate new client ID for API key users - use full UUID to prevent collisions
            client_id = f"client-{str(uuid.uuid4())}"
            logger.info(f"🔑 Generating JWT token via legacy API key for new client: {client_id}")
        else:
            # For JWT users, reuse their existing client_id
            client_id = current_user.get("client_id", f"client-{str(uuid.uuid4())}")
            logger.info(f"🔄 Generating JWT token via existing JWT for client: {client_id}")
        
        # Use default server expiration (n minutes)
        expires_in_minutes = jwt_manager.access_token_expire_minutes
        
        # Create JWT token with minimal session data
        session_data = {
            "created_at": timedelta(seconds=0).total_seconds(),  # Will be set by JWT manager
            "auto_generated": True
        }
        
        access_token = create_session_token(
            client_id=client_id,
            session_data=session_data,
            expires_delta=None  # Use default
        )
        
        # Get token info for response
        token_info = get_token_expiration_info(access_token)
        
        logger.info(f"🎟️ JWT token generated for auto-generated client: {client_id}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=expires_in_minutes,
            expires_at=token_info.get("expires_at", "unknown"),
            client_id=client_id
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )

@router.get("/token/info", response_model=TokenInfoResponse)
async def get_token_info(current_user = Security(get_current_user_jwt)):
    """
    Get information about the current JWT token
    
    Headers Required:
        Authorization: Bearer <your-jwt-token>
    
    Returns:
        Information about the token including expiration details
    """
    try:
        # Extract token from the Authorization header to get detailed info
        from fastapi import Request
        
        # The current_user already contains the payload, but let's get additional info
        token_info = {
            "valid": True,
            "client_id": current_user.get("client_id"),
            "issued_at": current_user.get("iat"),
            "expires_at": current_user.get("exp"),
            "token_type": current_user.get("type"),
            "session_type": current_user.get("session_type")
        }
        
        # Calculate expires_in_minutes from exp timestamp
        exp = current_user.get("exp")
        if exp:
            expires_at_dt = datetime.fromtimestamp(exp, timezone.utc)
            expires_in_minutes = int((expires_at_dt - datetime.now(timezone.utc)).total_seconds() / 60)
            token_info["expires_in_minutes"] = max(0, expires_in_minutes)
            token_info["expires_at"] = expires_at_dt.isoformat()
        
        # Convert iat timestamp to ISO format
        iat = current_user.get("iat")
        if iat:
            issued_at_dt = datetime.fromtimestamp(iat, timezone.utc)
            token_info["issued_at"] = issued_at_dt.isoformat()
        
        return TokenInfoResponse(**token_info)
        
    except Exception as e:
        logger.error(f"❌ Error getting token info: {e}")
        return TokenInfoResponse(
            valid=False,
            error=str(e)
        )

@router.post("/token/refresh")
async def refresh_jwt_token(
    current_user = Security(get_current_user_jwt),
    expires_in_minutes: Optional[int] = None
):
    """
    Refresh (regenerate) a JWT token using an existing valid token
    
    Headers Required:
        Authorization: Bearer <your-current-jwt-token>
    
    Query Parameters:
        expires_in_minutes: Optional custom expiration time for new token
    
    Returns:
        New JWT token with same client_id and session_data
    """
    try:
        # Extract relevant data from current token
        client_id = current_user.get("client_id", "anonymous")
        session_data = {
            k: v for k, v in current_user.items() 
            if k not in ["exp", "iat", "iss", "type", "sub"]
        }
        
        # Determine expiration time for new token
        expires_delta = None
        if expires_in_minutes:
            expires_delta = timedelta(minutes=expires_in_minutes)
            new_expires_in_minutes = expires_in_minutes
        else:
            new_expires_in_minutes = jwt_manager.access_token_expire_minutes
        
        # Create new JWT token
        new_access_token = create_session_token(
            client_id=client_id,
            session_data=session_data,
            expires_delta=expires_delta
        )
        
        # Get token info for response
        token_info = get_token_expiration_info(new_access_token)
        
        logger.info(f"🔄 JWT token refreshed for client: {client_id}")
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in_minutes=new_expires_in_minutes,
            expires_at=token_info.get("expires_at", "unknown"),
            client_id=client_id
        )
        
    except Exception as e:
        logger.error(f"❌ Error refreshing JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )

@router.delete("/token/revoke")
async def revoke_jwt_token(current_user = Security(get_current_user_jwt)):
    """
    Revoke (invalidate) the current JWT token
    
    Note: Since JWT tokens are stateless, this endpoint mainly serves as a 
    logout confirmation. The token will still be valid until its expiration time.
    For production use, consider implementing a token blacklist in Redis.
    
    Headers Required:
        Authorization: Bearer <your-jwt-token>
    
    Returns:
        Confirmation of token revocation
    """
    try:
        client_id = current_user.get("client_id", "anonymous")
        
        # In a full implementation, you would add the token to a blacklist in Redis
        # For now, we just log the revocation
        logger.info(f"🚫 JWT token revoked for client: {client_id}")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Token revoked successfully",
                "client_id": client_id,
                "remark": "Please obtain a new token to continue API access"
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"❌ Error revoking JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke token: {str(e)}"
        )

@router.get("/test-jwt")
async def test_jwt_authentication(current_user = Security(get_current_user_jwt)):
    """
    Test endpoint to verify JWT authentication is working
    
    Headers Required:
        Authorization: Bearer <your-jwt-token>
    
    Returns:
        Current user information from JWT token
    """
    return JSONResponse(
        content={
            "status": "success",
            "message": "JWT authentication successful",
            "user_info": current_user,
            "client_id": current_user.get("client_id"),
            "session_type": current_user.get("session_type")
        },
        status_code=status.HTTP_200_OK
    )
