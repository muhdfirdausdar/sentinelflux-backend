"""
JWT Session Authentication Module for SentinelFlux API

This module provides JWT-based session authenticati            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):as an alternative to API key authentication.
Users can obtain a JWT token from the /auth/token endpoint using the API key, and then use 
the JWT token for subsequent requests.

Flow:
1. User calls /auth/token with X-API-Key header to get JWT token
2. User uses JWT token in Authorization: Bearer <token> header for other endpoints
3. JWT tokens have configurable expiration time (default: 60 minutes)

Environment Variables:
    JWT_SECRET_KEY: Secret key for signing JWT tokens (defaults to a fallback key)
    JWT_ALGORITHM: Algorithm for JWT signing (default: HS256)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration time in minutes (default: 60)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv
from utils.async_log import get_logger

# Load environment variables
load_dotenv()

logger = get_logger("jwt_auth")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be set; refusing to use a predictable default")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Security scheme for Bearer token
security = HTTPBearer()

class JWTManager:
    """JWT Token Manager for SentinelFlux"""
    
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.access_token_expire_minutes = JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT access token
        
        Args:
            data: Payload data to encode in the token
            expires_delta: Custom expiration time (optional)
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": "sentinelflux-api",
            "type": "access_token"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"🔐 JWT token created, expires at {expire}")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate token type
            if payload.get("type") != "access_token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Validate issuer
            if payload.get("iss") != "sentinelflux-api":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer"
                )
            
            # Check if token has expired
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            logger.debug("✅ JWT token verified successfully")
            return payload
            
        except JWTError as e:
            logger.warning(f"❌ JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error during JWT verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Get information about a JWT token without full verification
        
        Args:
            token: JWT token string
            
        Returns:
            Token information dictionary
        """
        try:
            # Decode without verification to get payload info
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            exp = payload.get("exp")
            iat = payload.get("iat")
            
            info = {
                "valid": True,
                "issued_at": datetime.fromtimestamp(iat, timezone.utc).isoformat() if iat else None,
                "expires_at": datetime.fromtimestamp(exp, timezone.utc).isoformat() if exp else None,
                "subject": payload.get("sub"),
                "issuer": payload.get("iss"),
                "token_type": payload.get("type"),
                "expires_in_minutes": int((datetime.fromtimestamp(exp, timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 60) if exp else None
            }
            
            return info
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get token info: {e}")
            return {
                "valid": False,
                "error": str(e)
            }

# Global JWT manager instance
jwt_manager = JWTManager()

# FastAPI dependency for JWT authentication
async def get_current_user_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    FastAPI dependency to validate JWT token from Authorization: Bearer header
    
    Args:
        credentials: Bearer token credentials from request header
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Expected: Bearer"
        )
    
    try:
        payload = jwt_manager.verify_token(credentials.credentials)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in JWT dependency: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# Helper function to create session token
def create_session_token(
    client_id: str = "anonymous", 
    session_data: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a session JWT token
    
    Args:
        client_id: Identifier for the client/user
        session_data: Additional session data to include
        expires_delta: Custom expiration time
        
    Returns:
        JWT token string
    """
    payload = {
        "sub": client_id,
        "client_id": client_id,
        "session_type": "api_access"
    }
    
    if session_data:
        payload.update(session_data)
    
    return jwt_manager.create_access_token(payload, expires_delta)

# Helper function to get token expiration info
def get_token_expiration_info(token: str) -> Dict[str, Any]:
    """
    Get expiration information for a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with expiration information
    """
    return jwt_manager.get_token_info(token)
