# JWT Session Authentication for SentinelFlux API

This document explains the new JWT-based session authentication system for the SentinelFlux API.

## Overview

The SentinelFlux API now supports **hybrid authentication**:
1. **JWT Token Authentication** (Primary) - Modern, stateless session tokens
2. **API Key Authentication** (Legacy) - Traditional X-API-Key header method

### Key Features
- 🔐 **Secure JWT tokens** with configurable expiration
- 🔄 **Token refresh** capability 
- 🏠 **Hybrid support** - Both JWT and API key work together
- 📊 **Token introspection** - Get detailed token information
- ⚡ **Stateless** - No server-side session storage required

## Quick Start

### 1. Get a JWT Token

**Endpoint:** `POST /auth/token`
**Authentication:** X-API-Key (this is the ONLY endpoint that still uses the old API key)

**Standard Usage:**
```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "X-API-Key: YOUR_API_KEY"
```

That's it! The server will automatically:
- Generate a unique client ID
- Set appropriate expiration time (60 minutes)
- Create a secure JWT token

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer", 
  "expires_in_minutes": 60,
  "expires_at": "2024-01-01T12:00:00",
  "client_id": "auto-generated-uuid"
}
```

### 2. Use JWT Token for API Calls

For all other endpoints, use the JWT token:

```bash
curl -X GET "http://localhost:8000/domain?id=1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Authentication Methods

### JWT Token Authentication (Recommended)
```bash
# Header format
Authorization: Bearer <jwt-token>
```

### API Key Authentication (Legacy Support)
```bash
# Header format  
X-API-Key: <api-key>
```

### Hybrid Usage
The API accepts **both methods simultaneously**. If both are provided, JWT takes priority.

## API Endpoints

### Authentication Endpoints

#### `POST /auth/token`
Generate a new JWT token using API key authentication.

**Headers:**
- `X-API-Key: <your-api-key>`

**Body:** None required (empty body)

The server automatically handles:
- Client ID generation (UUID)
- Expiration time (60 minutes default)
- Token security and validation

#### `GET /auth/token/info`
Get information about your current JWT token.

**Headers:**
- `Authorization: Bearer <jwt-token>`

**Response:**
```json
{
  "valid": true,
  "issued_at": "2024-01-01T11:00:00",
  "expires_at": "2024-01-01T12:00:00", 
  "expires_in_minutes": 45,
  "client_id": "my-client",
  "token_type": "access_token"
}
```

#### `POST /auth/token/refresh`
Refresh (regenerate) your JWT token using current valid token.

**Headers:**
- `Authorization: Bearer <current-jwt-token>`

**Query Parameters:**
- `expires_in_minutes` (optional): Custom expiration for new token

#### `DELETE /auth/token/revoke`
Revoke (invalidate) your current JWT token.

**Headers:**
- `Authorization: Bearer <jwt-token>`

#### `GET /auth/test-jwt`
Test endpoint to verify JWT authentication is working.

**Headers:**
- `Authorization: Bearer <jwt-token>`

### All Other API Endpoints

All existing endpoints (`/domain`, `/vis/domain`, `/db_status`, `/dnflux/*`, etc.) now accept **both authentication methods**:

```bash
# Using JWT (recommended)
curl -H "Authorization: Bearer <jwt-token>" http://localhost:8000/domain?id=1

# Using API Key (legacy support)  
curl -H "X-API-Key: <api-key>" http://localhost:8000/domain?id=1
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY="your-secret-key-change-in-production"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES="60"

# Existing API Key (still used for /auth/token endpoint)
API_KEY="your-sentinelflux-api-key"
```

### Production Security
- Change `JWT_SECRET_KEY` to a strong, unique value
- Use HTTPS in production
- Consider shorter token expiration times for sensitive environments
- Monitor token usage and implement rate limiting

## Code Examples

### Python Example

```python
import requests

# Simple and clean - just get a token
token_response = requests.post("http://localhost:8000/auth/token", 
    headers={"X-API-Key": "your-api-key"})

token_data = token_response.json()
jwt_token = token_data["access_token"]

# Use JWT token for API calls
api_response = requests.get("http://localhost:8000/domain?id=1",
    headers={"Authorization": f"Bearer {jwt_token}"})

print(api_response.json())
```

### JavaScript Example

```javascript
// Simple and clean - just get a token
const tokenResponse = await fetch('http://localhost:8000/auth/token', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

const tokenData = await tokenResponse.json();
const jwtToken = tokenData.access_token;

// Use JWT token for API calls
const apiResponse = await fetch('http://localhost:8000/domain?id=1', {
  headers: {
    'Authorization': `Bearer ${jwtToken}`
  }
});

const data = await apiResponse.json();
console.log(data);
```

## Migration Guide

### For Existing Clients

**Option 1: Minimal Change (Hybrid)**
- Keep using X-API-Key headers
- No code changes needed
- Consider migrating to JWT gradually

**Option 2: Full JWT Migration**
1. Update your client to call `/auth/token` first
2. Store the JWT token
3. Use `Authorization: Bearer <token>` for all subsequent calls
4. Implement token refresh logic

### Benefits of Migrating to JWT
- **Better security**: Tokens expire automatically
- **Scalability**: Stateless authentication
- **Flexibility**: Include session data in tokens
- **Standards compliance**: Industry-standard JWT

## Demo Script

Run the included demonstration script:

```bash
# Make sure the API server is running
python main.py

# In another terminal, run the demo
python demo_jwt_auth.py
```

The demo script shows:
- Getting JWT tokens
- Using JWT for API calls  
- Token refresh
- Hybrid authentication support

## Error Handling

### Common JWT Errors

| Error | Status | Description | Solution |
|-------|--------|-------------|----------|
| `Invalid or expired token` | 401 | JWT token is malformed or expired | Get a new token |
| `Invalid token type` | 401 | Token is not an access token | Use correct token from `/auth/token` |
| `Authentication required` | 401 | No valid auth method provided | Provide JWT or API key |
| `Invalid or missing API key` | 401 | API key is wrong (only for `/auth/token`) | Check your API key |

### Best Practices

1. **Handle token expiration gracefully**
   ```python
   def api_call_with_retry(url, token):
       response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
       if response.status_code == 401:
           # Token expired, refresh and retry
           new_token = refresh_token(token)
           response = requests.get(url, headers={"Authorization": f"Bearer {new_token}"})
       return response
   ```

2. **Store tokens securely**
   - Don't hardcode tokens in source code
   - Use secure storage (keychain, environment variables)
   - Don't log tokens in plaintext

3. **Monitor token usage**
   - Track token issuance and usage
   - Set up alerts for unusual patterns
   - Implement rate limiting

## Implementation Details

### JWT Payload Structure

```json
{
  "sub": "client-id",
  "client_id": "client-id", 
  "session_type": "api_access",
  "iat": 1641024000,
  "exp": 1641027600,
  "iss": "sentinelflux-api",
  "type": "access_token",
  "custom_data": "from_session_data"
}
```

### Security Features

- **HMAC SHA-256** signature algorithm
- **Configurable expiration** (default: 60 minutes)
- **Issuer validation** (iss: "sentinelflux-api")
- **Token type validation** (type: "access_token")
- **Timestamp validation** (iat, exp claims)

### Backwards Compatibility

- All existing API key authentication continues to work
- No breaking changes to existing endpoints
- Gradual migration path available
- Hybrid authentication supports both methods

## Support

For questions or issues:
1. Check the demo script for working examples
2. Review error messages and status codes
3. Verify your API key and JWT token format
4. Check server logs for detailed error information

---

**Note**: The `/auth/token` endpoint is the ONLY endpoint that requires the old X-API-Key authentication. All other endpoints support both JWT and API key authentication methods.
