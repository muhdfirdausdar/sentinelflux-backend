"""
DNFlux Global Connection Pool
Maintains persistent HTTP connections to DNFlux VM2 service with failsafe features
Features: Dynamic API key management, auto-reconnection, health monitoring
"""

import asyncio
import os
from typing import Optional
import httpx
from datetime import datetime, timedelta
from utils.async_log import get_logger


logger = get_logger("dnflux_pool")

# Check if at local machine or not
AT_LOCAL_MACHINE = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')

if AT_LOCAL_MACHINE:
    logger.warning("Running on local machine")
else:
    logger.info("Running in production environment")




class DNFluxGlobalPool:
    """
    Global connection pool for DNFlux VM2 communication
    Initialized once and reused throughout the application lifecycle
    Features: Auto-reconnection, health monitoring, error handling
    """
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url: str = ""
        self._current_api_key: str = ""
        self._credential_source: str = ""
        self._initialized = False
        self._last_health_check: Optional[datetime] = None
        self._connection_healthy = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._health_check_interval = 120  # 2 minutes - reduced frequency
        self._apikey_manager = None  # Will be initialized on first use
    
    async def initialize(self):
        """Initialize the global connection pool - called once at startup"""
        if self._initialized:
            logger.info("🔄 DNFlux pool already initialized - reusing connection")
            return
        
        logger.info("🔧 Initializing DNFlux Global Connection Pool...")
        
        # Get credentials based on environment
        from utils.credential_manager import credential_manager
        creds = await credential_manager.get_dnflux_credentials()
        self._base_url = creds['base_url']
        self._current_api_key = creds['api_token']
        self._credential_source = creds['source']
        
        await self._create_client()
        
        self._initialized = True
        self._last_health_check = datetime.utcnow()
        self._connection_healthy = True
        self._reconnect_attempts = 0
        
        logger.info(f"✅ DNFlux Global Pool initialized - {self._base_url}")
        logger.info(f"🔑 Credentials source: {self._credential_source}")
        logger.info("🔗 Persistent connections ready for reuse")
        logger.info("🛡️ Failsafe features: Auto-reconnect, health monitoring enabled")
    
    async def _create_client(self):
        """Create the HTTP client with retry and timeout configuration"""
        if self._client:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.warning(f"⚠️ Error closing previous client: {e}")
        
        # Create persistent HTTP client with connection pooling and retries
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(60.0, connect=15.0, read=60.0),  # Increased timeouts
            limits=httpx.Limits(
                max_keepalive_connections=20,  # Increased for persistent use
                max_connections=100,           # Increased for concurrent requests
                keepalive_expiry=300.0        # 5 minutes keepalive
            ),
            headers={
                "X-API-Key": self._current_api_key,  # Use X-API-Key header
                "User-Agent": "SentinelFlux-Gateway/1.0",
                "Accept": "application/json",
                "Connection": "keep-alive"
            },
            # Enable connection retries
            transport=httpx.AsyncHTTPTransport(
                retries=1,  # Reduced retries since we handle retries manually
                verify=True
            )
        )
    
    def get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client with health check and auto-reconnection"""
        if not self._initialized or not self._client:
            raise RuntimeError("DNFlux pool not initialized. Call initialize() first.")
        
        # Check if we need to perform health check
        if self._should_health_check():
            # Run health check in background (don't wait for it)
            asyncio.create_task(self._background_health_check())
        
        return self._client
    
    def _should_health_check(self) -> bool:
        """Check if we should perform a health check"""
        if not self._last_health_check:
            return True
        
        time_since_check = datetime.utcnow() - self._last_health_check
        return time_since_check.total_seconds() > self._health_check_interval
    
    async def _background_health_check(self):
        """Perform background health check and auto-reconnect if needed"""
        try:
            logger.debug("🔍 Performing background health check...")
            
            # Try a simple health check using the actual metrics endpoint
            # This ensures we're testing the same endpoint that causes issues
            response = await self._client.get("/helper/metrics", timeout=10.0)
            
            if response.status_code == 200:
                if not self._connection_healthy:
                    logger.info("✅ DNFlux connection restored!")
                self._connection_healthy = True
                self._reconnect_attempts = 0
            else:
                logger.warning(f"⚠️ DNFlux health check failed: HTTP {response.status_code}")
                await self._handle_connection_failure()
                
            self._last_health_check = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"❌ DNFlux health check failed: {e}")
            await self._handle_connection_failure()
    
    async def _handle_connection_failure(self):
        """Handle connection failure with auto-reconnection"""
        self._connection_healthy = False
        
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            logger.warning(f"🔄 Attempting to reconnect ({self._reconnect_attempts}/{self._max_reconnect_attempts})...")
            
            try:
                # Wait before reconnecting (exponential backoff)
                wait_time = 2 ** self._reconnect_attempts
                await asyncio.sleep(wait_time)
                
                # Recreate the client
                await self._create_client()
                
                # Test the new connection
                response = await self._client.get("/helper/metrics", timeout=10.0)
                if response.status_code == 200:
                    logger.info(f"✅ DNFlux reconnection successful (attempt {self._reconnect_attempts})")
                    self._connection_healthy = True
                    self._reconnect_attempts = 0
                else:
                    logger.error(f"❌ Reconnection failed: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Reconnection attempt {self._reconnect_attempts} failed: {e}")
        else:
            logger.error(f"🚨 DNFlux connection permanently failed after {self._max_reconnect_attempts} attempts")
            logger.error("🛑 Manual intervention may be required")
    
    async def refresh_api_key(self) -> bool:
        """
        Manually refresh API key and recreate client
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("🔑 Refreshing API key...")
            from utils.credential_manager import credential_manager
            creds = await credential_manager.get_dnflux_credentials()
            self._current_api_key = creds['api_token']
            self._credential_source = creds['source']
            
            # Recreate client with refreshed key
            await self._create_client()
            
            # Test the new connection
            response = await self._client.get("/helper/metrics", timeout=10.0)
            if response.status_code == 200:
                logger.info(f"✅ API key refresh successful (source: {self._credential_source})")
                return True
            else:
                logger.error(f"❌ API key refresh failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ API key refresh failed: {e}")
            return False
    
    async def get_api_key_status(self) -> dict:
        """
        Get API key status information
        
        Returns:
            Dictionary with API key status
        """
        try:
            return {
                "current_key": self._current_api_key[:10] + "..." if self._current_api_key else None,
                "source": getattr(self, '_credential_source', 'unknown'),
                "connection_healthy": self._connection_healthy,
                "base_url": self._base_url,
                "environment": "local" if AT_LOCAL_MACHINE else "production"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get API key status: {e}")
            return {"error": str(e)}
    
    async def request_with_retry(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make HTTP request with automatic retry and reconnection
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for the request
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPError: If request fails after all retries
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Ensure client is available and healthy
                if not self._client:
                    logger.warning("🔄 Client not available, reinitializing...")
                    await self._create_client()
                
                client = self.get_client()
                response = await client.request(method, endpoint, **kwargs)
                
                # If we get here, request was successful
                if not self._connection_healthy:
                    logger.info("✅ DNFlux connection restored after retry")
                    self._connection_healthy = True
                    self._reconnect_attempts = 0
                
                return response
                
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, httpx.ReadError) as e:
                logger.warning(f"⚠️ DNFlux request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Trigger reconnection before next attempt
                    await self._handle_connection_failure()
                    await asyncio.sleep(2)  # Wait a bit longer before retry
                else:
                    logger.error(f"❌ DNFlux request failed permanently after {max_retries} attempts")
                    raise
            
            except Exception as e:
                logger.error(f"❌ Unexpected error in DNFlux request: {e}")
                if attempt < max_retries - 1:
                    # For unexpected errors, also try reconnection
                    await self._handle_connection_failure()
                    await asyncio.sleep(2)
                else:
                    raise
    
    async def close(self):
        """Close the global connection pool"""
        if self._client:
            await self._client.aclose()
            self._initialized = False
            self._connection_healthy = False
            logger.info("🔌 DNFlux Global Pool closed")
    
    async def reset_connection(self):
        """Manually reset the connection pool (useful for recovery)"""
        logger.info("🔄 Manually resetting DNFlux connection pool...")
        try:
            if self._client:
                await self._client.aclose()
            
            await self._create_client()
            self._connection_healthy = True
            self._reconnect_attempts = 0
            self._last_health_check = datetime.utcnow()
            
            logger.info("✅ DNFlux connection pool reset successfully")
        except Exception as e:
            logger.error(f"❌ Failed to reset connection pool: {e}")
            self._connection_healthy = False
    
    def get_url(self, endpoint: str) -> str:
        """Get full URL for endpoint"""
        return f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    def is_initialized(self) -> bool:
        """Check if the pool is initialized"""
        return self._initialized
    
    def is_healthy(self) -> bool:
        """Check if the connection is healthy"""
        return self._connection_healthy
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            'initialized': self._initialized,
            'healthy': self._connection_healthy,
            'base_url': self._base_url,
            'reconnect_attempts': self._reconnect_attempts,
            'max_reconnect_attempts': self._max_reconnect_attempts,
            'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'health_check_interval_seconds': self._health_check_interval
        }
    
    @property
    def base_url(self) -> str:
        """Get the base URL"""
        return self._base_url

# Global connection pool instance - initialized once in main.py
dnflux_pool = DNFluxGlobalPool()
