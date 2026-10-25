"""
DNFlux Metadata Handler
Handles all /helper/metrics operations
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from utils.async_log import get_logger
from utils.cache_keys import CacheKeys, CacheTTL
from redis_client import get_redis_engine
from dnflux_pool import dnflux_pool

logger = get_logger("metadata_handler")

async def get_metrics(use_cache: bool = True) -> Dict[str, Any]:
    """
    Get metrics from DNFlux /helper/metrics endpoint
    
    Args:
        use_cache: Whether to use cached data if available
        
    Returns:
        Dict containing metrics data
    """
    cache_key = CacheKeys.get_vm2_metadata_key()
    redis_client = await get_redis_engine()
    
    # Try cache first if requested
    if use_cache:
        cached_data = await _get_from_cache(cache_key, redis_client)
        if cached_data:
            logger.info("📊 Retrieved metrics from cache")
            return cached_data
    
    # Fetch fresh data from DNFlux VM2
    try:
        logger.info("🌐 Fetching fresh metrics from DNFlux VM2...")
        
        # Use the failsafe request method with retry and reconnection
        response = await dnflux_pool.request_with_retry("GET", "/helper/metrics")
        response.raise_for_status()
        
        metrics_data = response.json()
        
        # Add timestamp
        metrics_data['fetched_at'] = datetime.utcnow().isoformat()
        metrics_data['source'] = 'dnflux_vm2'
        
        # Cache the result
        await _save_to_cache(cache_key, metrics_data, CacheTTL.VM2_METADATA, redis_client)
        
        logger.info(f"✅ Retrieved fresh metrics: {len(metrics_data)} fields")
        return metrics_data
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch metrics: {e}")
        
        # Try to return stale cache data as fallback
        cached_data = await _get_from_cache(cache_key, redis_client)
        if cached_data:
            logger.warning("⚠️ Returning stale cached metrics as fallback")
            cached_data['stale_data'] = True
            return cached_data
        
        # No cache available, raise error
        raise Exception(f"Failed to fetch metrics and no cache available: {e}")

async def get_metadata_summary() -> Dict[str, Any]:
    """
    Get a summary of metadata statistics
    
    Returns:
        Dict containing summary statistics
    """
    try:
        metrics = await get_metrics(use_cache=True)
        
        # Generate summary statistics
        summary = {
            'total_domains': metrics.get('total_domains', 0),
            'total_ips': metrics.get('total_ips', 0),
            'fastflux_detections': metrics.get('fastflux_count', 0),
            'malicious_domains': metrics.get('malicious_count', 0),
            'last_updated': metrics.get('fetched_at'),
            'data_freshness': 'cached' if 'stale_data' not in metrics else 'stale'
        }
        
        logger.info("📈 Generated metadata summary")
        return summary
        
    except Exception as e:
        logger.error(f"❌ Failed to generate metadata summary: {e}")
        return {
            'error': f"Failed to fetch metadata: {str(e)}",
            'status': 'unavailable'
        }

async def clear_cache(pattern: str = None):
    """
    Clear metadata cache
    
    Args:
        pattern: Cache key pattern to clear (default: all metadata cache)
    """
    try:
        redis_client = await get_redis_engine()
        
        if not pattern:
            pattern = "vm2:metadata*"
        
        # Get keys matching pattern
        keys = await redis_client.keys(pattern)
        
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"🗑️ Cleared {len(keys)} cache entries matching: {pattern}")
        else:
            logger.info(f"ℹ️ No cache entries found matching: {pattern}")
            
    except Exception as e:
        logger.error(f"❌ Failed to clear cache: {e}")

async def _get_from_cache(cache_key: str, redis_client) -> Optional[Dict[str, Any]]:
    """Get data from Redis cache"""
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode('utf-8')
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"⚠️ Cache retrieval failed for {cache_key}: {e}")
    return None

async def _save_to_cache(cache_key: str, data: Dict[str, Any], ttl: int, redis_client):
    """Save data to Redis cache"""
    try:
        json_data = json.dumps(data, default=str)
        await redis_client.setex(cache_key, ttl, json_data)
        logger.debug(f"💾 Cached data with key: {cache_key} (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"⚠️ Cache storage failed for {cache_key}: {e}")
