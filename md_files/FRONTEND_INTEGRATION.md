# Frontend Integration Guide - JWT Authentication

## Super Simple JWT Authentication

For frontend developers, the JWT authentication is now extremely simple:

### 1. Get a Token (One-time setup)

```javascript
// Just make a POST request with your API key - no body needed!
const getToken = async () => {
  const response = await fetch('http://localhost:8000/auth/token', {
    method: 'POST',
    headers: {
      'X-API-Key': 'YOUR_API_KEY'
    }
  });
  
  const data = await response.json();
  return data.access_token;
};
```

### 2. Use Token for All API Calls

```javascript
// Use the token for all subsequent requests
const token = await getToken();

const apiCall = async (endpoint) => {
  const response = await fetch(`http://localhost:8000${endpoint}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};

// Example usage
const domainData = await apiCall('/domain?id=1');
const dbStatus = await apiCall('/db_status');
```

### 3. Complete Example

```javascript
class SentinelFluxAPI {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'http://localhost:8000';
    this.token = null;
  }
  
  async getToken() {
    const response = await fetch(`${this.baseUrl}/auth/token`, {
      method: 'POST',
      headers: { 'X-API-Key': this.apiKey }
    });
    
    const data = await response.json();
    this.token = data.access_token;
    return this.token;
  }
  
  async call(endpoint) {
    if (!this.token) {
      await this.getToken();
    }
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    // Handle token expiration
    if (response.status === 401) {
      await this.getToken(); // Get new token
      return this.call(endpoint); // Retry request
    }
    
    return response.json();
  }
}

// Usage
const api = new SentinelFluxAPI('YOUR_API_KEY');
const data = await api.call('/domain?id=1');
```

## That's It!

No complex parameters, no client IDs to manage, no expiration times to worry about. The server handles everything automatically:

- ✅ **Auto-generated client ID** (unique UUID)
- ✅ **Standard 60-minute expiration**
- ✅ **Secure token generation**
- ✅ **Automatic refresh when needed**

## React Example

```jsx
import { useState, useEffect } from 'react';

const useSentinelFluxAPI = (apiKey) => {
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const getToken = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/auth/token', {
        method: 'POST',
        headers: { 'X-API-Key': apiKey }
      });
      const data = await response.json();
      setToken(data.access_token);
      return data.access_token;
    } finally {
      setLoading(false);
    }
  };
  
  const apiCall = async (endpoint) => {
    const currentToken = token || await getToken();
    
    const response = await fetch(`http://localhost:8000${endpoint}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (response.status === 401) {
      const newToken = await getToken();
      return apiCall(endpoint); // Retry with new token
    }
    
    return response.json();
  };
  
  return { apiCall, loading, getToken };
};

// Component usage
const DomainComponent = () => {
  const { apiCall } = useSentinelFluxAPI('YOUR_API_KEY');
  const [data, setData] = useState(null);
  
  useEffect(() => {
    apiCall('/domain?id=1').then(setData);
  }, []);
  
  return <div>{JSON.stringify(data)}</div>;
};
```

## Curl Examples

```bash
# Step 1: Get token (no body needed)
curl -X POST "http://localhost:8000/auth/token" \
  -H "X-API-Key: YOUR_API_KEY"

# Response: {"access_token": "eyJ...", "token_type": "bearer", ...}

# Step 2: Use token for API calls
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/domain?id=1"
```

That's it! Maximum simplicity for frontend integration.
