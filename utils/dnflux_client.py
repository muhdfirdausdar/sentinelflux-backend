"""
DNFlux API Client Module

This module handles communication with the DNFlux VM2 service,
including data fetching, caching, and error handling.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx
from fastapi import HTTPException

from utils.async_log import get_logger
from utils.http_factory import HTTPClientFactory, get_vm2_url
from utils.cache_keys import CacheKeys, CacheTTL, CacheConfig
from redis_client import get_redis_engine

logger = get_logger("dnflux_client")

class DNFluxClient:
    """
    Client for communicating with DNFlux VM2 service
    """
    
    def __init__(self):
        self.redis_client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the DNFlux client"""
        if self._initialized:
            return
        
        logger.info("🔧 Initializing DNFlux Client...")
        
        # Initialize HTTP factory
        await HTTPClientFactory.initialize()
        
        # Get Redis client
        self.redis_client = await get_redis_engine()
        
        self._initialized = True
        logger.info("✅ DNFlux Client initialized")
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from Redis cache"""
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                CacheConfig.log_cache_operation("HIT", cache_key)
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Cache get error for key {cache_key}: {e}")
        
        CacheConfig.log_cache_operation("MISS", cache_key)
        return None
    
    async def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int):
        """Set data in Redis cache"""
        try:
            await self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(data, default=str)
            )
            CacheConfig.log_cache_operation("SET", cache_key, ttl)
        except Exception as e:
            logger.error(f"Cache set error for key {cache_key}: {e}")
    
    async def _make_request(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to DNFlux VM2"""
        if not self._initialized:
            await self.initialize()
        
        try:
            client = await HTTPClientFactory.get_client('vm2')
            url = await get_vm2_url(endpoint)
            
            logger.debug(f"Making request to: {url}")
            
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Received data from {endpoint}: {len(str(data))} chars")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {endpoint}: {e}")
            raise HTTPException(
                status_code=502, 
                detail=f"DNFlux VM2 error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"Request error for {endpoint}: {e}")
            raise HTTPException(
                status_code=502, 
                detail=f"DNFlux VM2 unavailable: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Internal error: {str(e)}"
            )
    
    async def get_metadata_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get metadata metrics from DNFlux VM2
        
        Args:
            use_cache: Whether to use Redis caching
            
        Returns:
            Dict containing metadata metrics
        """
        cache_key = CacheKeys.VM2_METADATA
        
        # Try cache first
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Fetch from VM2
        logger.info("📊 Fetching metadata metrics from DNFlux VM2...")
        data = await self._make_request('/helper/metrics')
        
        # Cache the result
        if use_cache:
            await self._set_cache(cache_key, data, CacheTTL.VM2_DATA)
        
        return data
    
    async def get_system_status(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get system status from DNFlux VM2
        
        Args:
            use_cache: Whether to use Redis caching
            
        Returns:
            Dict containing system status
        """
        cache_key = CacheKeys.VM2_DATA
        
        # Try cache first
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Fetch from VM2
        logger.info("📊 Fetching system status from DNFlux VM2...")
        data = await self._make_request('/health')
        
        # Cache the result
        if use_cache:
            await self._set_cache(cache_key, data, CacheTTL.SHORT)
        
        return data
    
    async def get_domain_analysis(self, domain_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get domain analysis from DNFlux VM2
        
        Args:
            domain_id: Domain ID to analyze
            use_cache: Whether to use Redis caching
            
        Returns:
            Dict containing domain analysis
        """
        cache_key = f"vm2:domain_analysis:{domain_id}"
        
        # Try cache first
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Fetch from VM2
        logger.info(f"📊 Fetching domain analysis for ID {domain_id} from DNFlux VM2...")
        data = await self._make_request(f'/domain/analysis?id={domain_id}')
        
        # Cache the result
        if use_cache:
            await self._set_cache(cache_key, data, CacheTTL.MEDIUM)
        
        return data
    
    async def bulk_health_check(self) -> Dict[str, bool]:
        """
        Perform bulk health check on DNFlux VM2 endpoints
        
        Returns:
            Dict mapping endpoint names to health status
        """
        logger.info("🏥 Performing bulk health check on DNFlux VM2...")
        
        endpoints = {
            'health': '/health',
            'metadata': '/helper/metrics',
            'status': '/status'
        }
        
        results = {}
        client = await HTTPClientFactory.get_client('vm2')
        
        for name, endpoint in endpoints.items():
            try:
                url = await get_vm2_url(endpoint)
                response = await client.get(url, timeout=5.0)
                results[name] = response.status_code == 200
                
                if results[name]:
                    logger.debug(f"✅ {name} endpoint healthy")
                else:
                    logger.warning(f"⚠️ {name} endpoint unhealthy: {response.status_code}")
                    
            except Exception as e:
                results[name] = False
                logger.error(f"❌ {name} endpoint error: {e}")
        
        overall_health = all(results.values())
        logger.info(f"🏥 DNFlux VM2 overall health: {'✅ HEALTHY' if overall_health else '❌ UNHEALTHY'}")
        
        return results
    
    async def clear_cache(self, pattern: str = "vm2:*"):
        """
        Clear cache entries matching pattern
        
        Args:
            pattern: Redis key pattern to match
        """
        try:
            # Get all keys matching pattern
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"🧹 Cleared {len(keys)} cache entries matching '{pattern}'")
            else:
                logger.info(f"🧹 No cache entries found matching '{pattern}'")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

# Global DNFlux client instance
dnflux_client = DNFluxClient()

# Convenience functions
async def get_dnflux_metadata(use_cache: bool = True) -> Dict[str, Any]:
    """Get DNFlux metadata - convenience function"""
    return await dnflux_client.get_metadata_metrics(use_cache)

async def get_dnflux_status(use_cache: bool = True) -> Dict[str, Any]:
    """Get DNFlux status - convenience function"""
    return await dnflux_client.get_system_status(use_cache)

async def test_dnflux_connection() -> bool:
    """Test DNFlux connection - for use in critical connection testing"""
    try:
        await dnflux_client.initialize()
        health_results = await dnflux_client.bulk_health_check()
        return any(health_results.values())  # Return True if any endpoint is healthy
    except Exception as e:
        logger.error(f"DNFlux connection test failed: {e}")
        return False

# Example usage
if __name__ == "__main__":
    async def test_client():
        await dnflux_client.initialize()
        
        try:
            # Test metadata endpoint
            metadata = await dnflux_client.get_metadata_metrics()
            print(f"Metadata: {metadata}")
            
            # Test health check
            health = await dnflux_client.bulk_health_check()
            print(f"Health: {health}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(test_client())
