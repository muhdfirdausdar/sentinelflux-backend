"""
Async HTTP Connection Factory and Pool Management

This module provides reusable HTTP client connections with proper
credential management and environment-aware configuration.
"""

import os
import asyncio
from typing import Optional, Dict, Any
import httpx
from utils.async_log import get_logger
from utils.azure_vault import vault_client

logger = get_logger("http_factory")

class HTTPClientFactory:
    """
    Factory for creating and managing HTTP client connections
    """
    
    _clients: Dict[str, httpx.AsyncClient] = {}
    _initialized = False
    
    @classmethod
    async def initialize(cls):
        """Initialize the HTTP client factory"""
        if cls._initialized:
            return
        
        logger.info("🔧 Initializing HTTP Client Factory...")
        
        # Check if running on local machine
        at_local = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')
        
        if at_local:
            # Local development configuration
            cls.vm2_url = "http://127.0.0.1:7272"
            cls.internal_token = os.getenv("DNFLUX_INTERNAL_TOKEN")
            if not cls.internal_token:
                raise RuntimeError("DNFLUX_INTERNAL_TOKEN must be set for local development")
            logger.info("🏠 Using LOCAL HTTP configuration")
        else:
            # Production configuration
            cls.vm2_url = os.getenv('DNFLUX_VM2_URL', '')
            if not cls.vm2_url:
                raise RuntimeError("DNFLUX_VM2_URL must be set for production configuration")
            try:
                cls.internal_token = await vault_client.get_dnflux_apikey()
                if not cls.internal_token:
                    # Fallback to environment variable
                    cls.internal_token = os.getenv('DNFLUX_INTERNAL_TOKEN')
                    logger.warning("⚠️ Using fallback DNFlux internal token from environment")
            except Exception as e:
                logger.error(f"Failed to get internal token from vault: {e}")
                cls.internal_token = os.getenv('DNFLUX_INTERNAL_TOKEN')
            logger.info("🏭 Using PRODUCTION HTTP configuration")
        
        # Create default client
        await cls._create_client('default')
        cls._initialized = True
        logger.info("✅ HTTP Client Factory initialized")
    
    @classmethod
    async def _create_client(cls, client_name: str, **kwargs) -> httpx.AsyncClient:
        """Create a new HTTP client with default configuration"""
        default_config = {
            'timeout': httpx.Timeout(30.0, connect=10.0),
            'limits': httpx.Limits(max_keepalive_connections=20, max_connections=100),
            'headers': {
                'User-Agent': 'SentinelFlux-Gateway/2.0',
                'X-Internal-Token': cls.internal_token
            }
        }
        
        # Merge with custom config
        config = {**default_config, **kwargs}
        
        client = httpx.AsyncClient(**config)
        cls._clients[client_name] = client
        
        logger.debug(f"Created HTTP client: {client_name}")
        return client
    
    @classmethod
    async def get_client(cls, client_name: str = 'default') -> httpx.AsyncClient:
        """Get an HTTP client by name"""
        if not cls._initialized:
            await cls.initialize()
        
        if client_name not in cls._clients:
            await cls._create_client(client_name)
        
        return cls._clients[client_name]
    
    @classmethod
    async def create_vm2_client(cls) -> httpx.AsyncClient:
        """Create a specialized client for VM2 communication"""
        return await cls.get_client('vm2')
    
    @classmethod
    async def close_all(cls):
        """Close all HTTP clients"""
        logger.info("🔌 Closing all HTTP clients...")
        for name, client in cls._clients.items():
            try:
                await client.aclose()
                logger.debug(f"Closed HTTP client: {name}")
            except Exception as e:
                logger.error(f"Error closing client {name}: {e}")
        
        cls._clients.clear()
        cls._initialized = False
        logger.info("✅ All HTTP clients closed")
    
    @classmethod
    def get_vm2_url(cls, endpoint: str = "") -> str:
        """Get the full VM2 URL for an endpoint"""
        if not cls._initialized:
            raise RuntimeError("HTTPClientFactory not initialized")
        
        base_url = cls.vm2_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        
        if endpoint:
            return f"{base_url}/{endpoint}"
        return base_url

class ConnectionPool:
    """
    Connection pool manager for different services
    """
    
    def __init__(self):
        self.factory = HTTPClientFactory()
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def start_health_checks(self):
        """Start periodic health checks for connections"""
        if self._health_check_task:
            return
        
        logger.info("🏥 Starting connection health checks...")
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop_health_checks(self):
        """Stop health check tasks"""
        if self._health_check_task:
            logger.info("🛑 Stopping connection health checks...")
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
    
    async def _health_check_loop(self):
        """Background task for health checking"""
        while True:
            try:
                await self.health_check_vm2()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self._health_check_interval)
    
    async def health_check_vm2(self) -> bool:
        """Check if VM2 is accessible"""
        try:
            client = await HTTPClientFactory.get_client()
            url = HTTPClientFactory.get_vm2_url('/health')
            
            response = await client.get(url, timeout=5.0)
            is_healthy = response.status_code == 200
            
            if is_healthy:
                logger.debug("✅ VM2 health check passed")
            else:
                logger.warning(f"⚠️ VM2 health check failed: {response.status_code}")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"❌ VM2 health check error: {e}")
            return False

# Global connection pool instance
connection_pool = ConnectionPool()

# Convenience functions
async def get_http_client(client_name: str = 'default') -> httpx.AsyncClient:
    """Get an HTTP client - convenience function"""
    return await HTTPClientFactory.get_client(client_name)

async def get_vm2_url(endpoint: str = "") -> str:
    """Get VM2 URL - convenience function"""
    await HTTPClientFactory.initialize()  # Ensure initialized
    return HTTPClientFactory.get_vm2_url(endpoint)

async def test_vm2_connection() -> bool:
    """Test VM2 connection - for use in critical connection testing"""
    try:
        await HTTPClientFactory.initialize()
        return await connection_pool.health_check_vm2()
    except Exception as e:
        logger.error(f"VM2 connection test failed: {e}")
        return False

# Example usage
if __name__ == "__main__":
    async def test_factory():
        await HTTPClientFactory.initialize()
        client = await HTTPClientFactory.get_client()
        
        print(f"VM2 URL: {HTTPClientFactory.get_vm2_url()}")
        print(f"VM2 Metadata URL: {HTTPClientFactory.get_vm2_url('/helper/metrics')}")
        
        await HTTPClientFactory.close_all()
    
    asyncio.run(test_factory())
