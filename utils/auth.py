"""
Authentication utilities for the SentinelFlux API

This module provides authentication dependencies for different security requirements:

1. get_current_user() - DEFAULT: JWT-only authentication for all routes
2. get_current_user_with_legacy() - SPECIAL: JWT + legacy API key for /auth/token ONLY
3. get_api_key() - LEGACY: API key only for specific use cases

Authentication Flow:
- Client uses X-API-Key header on /auth/token to get JWT token
- Client uses Authorization: Bearer <jwt-token> for ALL other endpoints
- No other endpoint accepts X-API-Key header

Configuration:
  - Local Development: Set AT_LOCAL_MACHINE=true, uses hardcoded API key from local_credentials.py
  - Production: Uses API_KEY environment variable or Azure Key Vault secret 'sf-apikey'
  
    API keys must be provided through local credentials or environment variables;
    they must never be stored in source control.
Azure Key Vault Secret Name: sf-apikey
"""

import os
from fastapi import HTTPException, Security, status, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Union, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if running on local machine
AT_LOCAL_MACHINE = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')

# Define the API key header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Define Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

# Load the valid API key based on environment
if AT_LOCAL_MACHINE:
    try:
        from utils.local_credentials import get_local_credentials
        api_creds = get_local_credentials('api_key')
        VALID_API_KEY = api_creds['sentinelflux_api_key']
        print(f"🏠 Using local API key for development")
    except Exception as e:
        print(f"⚠️ Failed to load local API key credentials: {e}")
        VALID_API_KEY = os.getenv("API_KEY")
else:
    # Production: Do not fetch API key at import time
    VALID_API_KEY = None


# Legacy API key dependency (used only for /auth/token endpoint)
async def get_api_key(api_key: str = Security(api_key_header)):
    """
    FastAPI dependency to validate API key from X-API-Key header
    This is LEGACY authentication - only used for /auth/token endpoint
    """
    if AT_LOCAL_MACHINE:
        valid_api_key = VALID_API_KEY
    else:
        from utils.credential_manager import credential_manager
        creds = await credential_manager.get_sentinelflux_api_key()
        valid_api_key = creds['api_key']
        
        if not valid_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API_KEY is not set in environment variables or Azure Key Vault."
            )
    if api_key != valid_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


# JWT-only authentication dependency (default for all routes)
async def get_current_user(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
):
    """
    JWT-only authentication dependency - this is the DEFAULT for all routes
    
    Only accepts JWT tokens via Authorization: Bearer <token>
    Use this for all routes except /auth/token which should use get_current_user_with_legacy
    
    Returns:
        Decoded JWT token payload
    """
    if not bearer_token or not bearer_token.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token required"
        )
    
    try:
        from utils.jwt_auth import jwt_manager
        payload = jwt_manager.verify_token(bearer_token.credentials)
        payload["auth_method"] = "jwt"
        return payload
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT token"
        )


# Legacy authentication dependency (ONLY for /auth/token endpoint)
async def get_current_user_with_legacy(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header)
):
    """
    Authentication dependency with legacy API key support
    
    **WARNING: Only use this for the /auth/token endpoint!**
    
    Priority:
    1. JWT Token (Authorization: Bearer <token>) - Primary method
    2. API Key (X-API-Key: <key>) - Legacy method (ONLY for /auth/token)
    
    Returns:
        For JWT: Decoded token payload
        For API Key: {"auth_method": "api_key", "client_id": "api_key_user"}
    """
    # Try JWT authentication first
    if bearer_token and bearer_token.credentials:
        try:
            from utils.jwt_auth import jwt_manager
            payload = jwt_manager.verify_token(bearer_token.credentials)
            payload["auth_method"] = "jwt"
            return payload
        except HTTPException:
            # JWT failed, try API key fallback
            pass
        except Exception:
            # Unexpected JWT error, try API key fallback
            pass
    
    # Try API key authentication as fallback (ONLY allowed here!)
    if api_key:
        try:
            if AT_LOCAL_MACHINE:
                valid_api_key = VALID_API_KEY
            else:
                from utils.credential_manager import credential_manager
                creds = await credential_manager.get_sentinelflux_api_key()
                valid_api_key = creds['api_key']
                
                if not valid_api_key:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="API_KEY is not set in environment variables or Azure Key Vault."
                    )
            
            if api_key == valid_api_key:
                return {
                    "auth_method": "api_key",
                    "client_id": "api_key_user",
                    "sub": "api_key_user",
                    "session_type": "api_key_legacy"
                }
        except HTTPException:
            raise
        except Exception:
            pass
    
    # Both authentication methods failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Use JWT token (Authorization: Bearer) or API key (X-API-Key) for /auth/token endpoint only"
    )


# JWT-only authentication dependency (strict JWT enforcement)
async def get_current_user_jwt_only():
    """
    Strict JWT-only authentication dependency
    Use this for endpoints that should ONLY accept JWT tokens
    """
    from utils.jwt_auth import get_current_user_jwt
    return await get_current_user_jwt()


# API-key-only authentication dependency (for legacy endpoints)
async def get_current_user_api_key_only(api_key: str = Security(api_key_header)):
    """
    API key only authentication dependency
    Use this for endpoints that should ONLY accept API keys (like /auth/token)
    """
    return await get_api_key(api_key)
