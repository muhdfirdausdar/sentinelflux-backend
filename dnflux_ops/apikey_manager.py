"""
DNFlux API Key Manager
Handles fetching, caching, and refreshing API keys from DNFlux VM2
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from utils.async_log import get_logger
from utils.cache_keys import CacheKeys, CacheTTL
from redis_client import get_redis_engine

logger = get_logger("dnflux_apikey")

# Check if running on local machine
AT_LOCAL_MACHINE = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')

class DNFluxAPIKeyManager:
    """
    Manages DNFlux API keys with automatic fetching and Redis buffering
    """
    
    def __init__(self):
        self._current_api_key: Optional[str] = None
        self._key_expires_at: Optional[datetime] = None
        self._refresh_buffer_minutes = 5  # Refresh 5 minutes before expiry
    
    async def get_api_key(self, force_refresh: bool = False) -> str:
        """
        Get valid API key, fetching from VM2 if needed
        
        Args:
            force_refresh: Force fetch new key even if current one is valid
            
        Returns:
            Valid API key string
            
        Raises:
            Exception: If unable to get valid API key
        """
        # Check if we have a valid cached key
        if not force_refresh and await self._has_valid_cached_key():
            cached_key = await self._get_cached_key()
            if cached_key:
                logger.debug("🔑 Using cached API key")
                return cached_key
        
        # Fetch new key from VM2
        logger.info("🌐 Fetching fresh API key from DNFlux VM2...")
        return await self._fetch_and_cache_key()
    
    async def _has_valid_cached_key(self) -> bool:
        """Check if we have a valid cached API key"""
        try:
            redis_client = await get_redis_engine()
            cache_key = CacheKeys.get_dnflux_apikey_key()
            
            # Check if key exists in cache
            cached_data = await redis_client.get(cache_key)
            if not cached_data:
                return False
            
            # Parse cached data
            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode('utf-8')
            key_data = json.loads(cached_data)
            
            # Check expiration
            expires_at = datetime.fromisoformat(key_data['expires_at'])
            buffer_time = timedelta(minutes=self._refresh_buffer_minutes)
            
            # Return False if key expires within buffer time
            return datetime.utcnow() + buffer_time < expires_at
            
        except Exception as e:
            logger.warning(f"⚠️ Error checking cached API key: {e}")
            return False
    
    async def _get_cached_key(self) -> Optional[str]:
        """Get API key from cache"""
        try:
            redis_client = await get_redis_engine()
            cache_key = CacheKeys.get_dnflux_apikey_key()
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                key_data = json.loads(cached_data)
                return key_data['api_key']
                
        except Exception as e:
            logger.warning(f"⚠️ Error retrieving cached API key: {e}")
        
        return None
    
    async def _fetch_and_cache_key(self) -> str:
        """Fetch new API key from VM2 and cache it"""
        try:
            # Import here to avoid circular imports
            from dnflux_pool import dnflux_pool
            
            # Get bootstrap key based on environment
            if AT_LOCAL_MACHINE:
                # Local development - use local credentials
                logger.info("🏠 Using local credentials for DNFlux API key")
                from utils.credential_manager import credential_manager
                creds = await credential_manager.get_dnflux_credentials()
                bootstrap_key = creds['api_token']
                base_url = creds['base_url']
            else:
                # Production - use Azure Key Vault
                logger.info("🏭 Using Azure Key Vault for DNFlux API key")
                from utils.credential_manager import credential_manager
                creds = await credential_manager.get_dnflux_credentials()
                bootstrap_key = creds['api_token']
                base_url = creds['base_url']
            
            # Create a temporary client for API key fetching
            import httpx
            async with httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Bearer {bootstrap_key}",
                    "User-Agent": "SentinelFlux-APIKeyManager/1.0",
                    "Accept": "application/json"
                }
            ) as client:
                
                # Fetch new API key
                response = await client.post("/auth/generate-key", json={
                    "client_id": "sentinelflux-gateway",
                    "duration_hours": 24,  # 24-hour keys
                    "permissions": ["read:metadata", "read:health"]
                })
                
                if response.status_code == 200:
                    key_data = response.json()
                    api_key = key_data['api_key']
                    expires_at = datetime.fromisoformat(key_data['expires_at'])
                    
                    # Cache the new key
                    await self._cache_api_key(api_key, expires_at)
                    
                    logger.info(f"✅ New API key obtained, expires at {expires_at}")
                    return api_key
                
                elif response.status_code == 404:
                    # Endpoint doesn't exist, fall back to bootstrap key
                    logger.info("ℹ️ API key endpoint not available, using bootstrap key")
                    return bootstrap_key
                
                else:
                    raise Exception(f"Failed to fetch API key: HTTP {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to fetch API key: {e}")
            
            # Fall back to bootstrap key based on environment
            if AT_LOCAL_MACHINE:
                logger.warning("⚠️ Falling back to local bootstrap API key")
                from utils.credential_manager import credential_manager
                creds = await credential_manager.get_dnflux_credentials()
                return creds['api_token']
            else:
                logger.warning("⚠️ Falling back to vault/environment bootstrap API key")
                from utils.credential_manager import credential_manager
                creds = await credential_manager.get_dnflux_credentials()
                return creds['api_token']
    
    async def _cache_api_key(self, api_key: str, expires_at: datetime):
        """Cache API key in Redis"""
        try:
            redis_client = await get_redis_engine()
            cache_key = CacheKeys.get_dnflux_apikey_key()
            
            # Prepare cache data
            cache_data = {
                'api_key': api_key,
                'expires_at': expires_at.isoformat(),
                'cached_at': datetime.utcnow().isoformat(),
                'source': 'dnflux_vm2'
            }
            
            # Calculate TTL (cache until expiry minus buffer)
            buffer_time = timedelta(minutes=self._refresh_buffer_minutes)
            ttl_seconds = int((expires_at - datetime.utcnow() - buffer_time).total_seconds())
            
            if ttl_seconds > 0:
                json_data = json.dumps(cache_data)
                await redis_client.setex(cache_key, ttl_seconds, json_data)
                logger.info(f"💾 API key cached for {ttl_seconds} seconds")
            else:
                logger.warning("⚠️ API key expires too soon, not caching")
                
        except Exception as e:
            logger.error(f"❌ Failed to cache API key: {e}")
    
    async def refresh_key(self) -> str:
        """Force refresh API key"""
        logger.info("🔄 Force refreshing API key...")
        return await self.get_api_key(force_refresh=True)
    
    async def get_key_info(self) -> Dict[str, Any]:
        """Get information about current API key"""
        try:
            redis_client = await get_redis_engine()
            cache_key = CacheKeys.get_dnflux_apikey_key()
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                key_data = json.loads(cached_data)
                
                expires_at = datetime.fromisoformat(key_data['expires_at'])
                time_to_expiry = expires_at - datetime.utcnow()
                
                return {
                    'has_cached_key': True,
                    'expires_at': key_data['expires_at'],
                    'time_to_expiry_minutes': int(time_to_expiry.total_seconds() / 60),
                    'cached_at': key_data['cached_at'],
                    'source': key_data['source'],
                    'needs_refresh': time_to_expiry.total_seconds() < (self._refresh_buffer_minutes * 60)
                }
            else:
                return {
                    'has_cached_key': False,
                    'needs_refresh': True
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting key info: {e}")
            return {
                'has_cached_key': False,
                'needs_refresh': True,
                'error': str(e)
            }
    
    async def clear_cached_key(self):
        """Clear cached API key (force refresh on next request)"""
        try:
            redis_client = await get_redis_engine()
            cache_key = CacheKeys.get_dnflux_apikey_key()
            await redis_client.delete(cache_key)
            logger.info("🗑️ Cached API key cleared")
        except Exception as e:
            logger.error(f"❌ Failed to clear cached API key: {e}")

# Global API key manager instance
dnflux_apikey_manager = DNFluxAPIKeyManager()
