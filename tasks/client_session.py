"""
Client Session Management for Live Map SSE Connections

This module handles Redis-based session tracking for SSE clients,
storing last_domain_id and last_live_map_update for incremental data fetching.

Session Structure:
    Key: visualize:live_map:{client_id}
    Type: Hash
    Fields:
        - last_domain_id: Last domain ID processed
        - last_live_map_update: Last update timestamp
    TTL: 300 seconds (5 minutes)
"""

from typing import Optional, Tuple
from redis_client import get_redis_engine
from utils.async_log import get_logger
from utils.cache_keys import CacheKeys

logger = get_logger("client_session")

# Session TTL in seconds (5 minutes)
SESSION_TTL = 300


async def get_session_info(client_id: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Get last_domain_id and last_live_map_update from Redis session.
    
    Args:
        client_id: Unique client identifier (from JWT)
    
    Returns:
        Tuple of (last_domain_id, last_live_map_update)
        Returns (None, None) if session not found
    
    Example:
        domain_id, last_update = await get_session_info("client-a82325d7-1ff0-4055-80fc-88297fa8ff9b")
        # (140996, "2025-10-12 21:14:04.730609")
    """
    try:
        redis = await get_redis_engine()
        key = f"{CacheKeys.LIVE_MAP_SESSION_DATA}:{client_id}"
        
        # Get both hash fields at once
        result = await redis.hmget(key, "last_domain_id", "last_live_map_update")
        
        if result[0] is None or result[1] is None:
            logger.info(f"No session found for client: {client_id}")
            return None, None
        
        last_domain_id = int(result[0])
        last_live_map_update = result[1]
        
        logger.debug(f"Session retrieved for {client_id}: domain_id={last_domain_id}, last_update={last_live_map_update}")
        return last_domain_id, last_live_map_update
        
    except Exception as e:
        logger.error(f"Error getting session info for {client_id}: {e}")
        return None, None


async def update_session_info(
    client_id: str,
    last_domain_id: int,
    last_live_map_update: str
) -> bool:
    """
    Create or update session info in Redis atomically using pipeline.
    
    Args:
        client_id: Unique client identifier (from JWT)
        last_domain_id: Latest domain ID processed
        last_live_map_update: Latest update timestamp (string format)
    
    Returns:
        True if operation succeeded, False otherwise
    
    Example:
        success = await update_session_info(
            "client-a82325d7-1ff0-4055-80fc-88297fa8ff9b",
            140996,
            "2025-10-12 21:14:04.730609"
        )
    """
    try:
        redis = await get_redis_engine()
        key = f"{CacheKeys.LIVE_MAP_SESSION_DATA}:{client_id}"
        
        # Use pipeline for atomic operations
        async with redis.pipeline(transaction=True) as pipe:
            # HSET creates the key if it doesn't exist, updates if it does
            await pipe.hset(
                key,
                mapping={
                    "last_domain_id": str(last_domain_id),
                    "last_live_map_update": last_live_map_update
                }
            )
            # Set expiration
            await pipe.expire(key, SESSION_TTL)
            
            # Execute atomically
            await pipe.execute()
        
        logger.info(f"Session updated for {client_id}: domain_id={last_domain_id}, last_update={last_live_map_update}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating session info for {client_id}: {e}")
        return False


async def refresh_session_expiry(client_id: str) -> bool:
    """
    Refresh the TTL of an existing session to prevent expiration.
    
    Args:
        client_id: Unique client identifier (from JWT)
    
    Returns:
        True if operation succeeded, False otherwise
    
    Example:
        success = await refresh_session_expiry("client-a82325d7-1ff0-4055-80fc-88297fa8ff9b")
    """
    try:
        redis = await get_redis_engine()
        key = f"{CacheKeys.LIVE_MAP_SESSION_DATA}:{client_id}"
        
        # Use pipeline for atomic operation (though single operation, good practice)
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.expire(key, SESSION_TTL)
            result = await pipe.execute()
        
        # Check if key exists (expire returns 1 if key exists, 0 if not)
        if result[0] == 1:
            logger.debug(f"Session expiry refreshed for {client_id}")
            return True
        else:
            logger.warning(f"Session not found for expiry refresh: {client_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error refreshing session expiry for {client_id}: {e}")
        return False


async def delete_session(client_id: str) -> bool:
    """
    Delete a client session from Redis (called on disconnect).
    
    Args:
        client_id: Unique client identifier (from JWT)
    
    Returns:
        True if operation succeeded, False otherwise
    
    Example:
        success = await delete_session("client-a82325d7-1ff0-4055-80fc-88297fa8ff9b")
    """
    try:
        redis = await get_redis_engine()
        key = f"{CacheKeys.LIVE_MAP_SESSION_DATA}:{client_id}"
        
        result = await redis.delete(key)
        
        if result == 1:
            logger.info(f"Session deleted for {client_id}")
            return True
        else:
            logger.warning(f"Session not found for deletion: {client_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error deleting session for {client_id}: {e}")
        return False


async def cleanup_stale_sessions(max_age_seconds: int = 300) -> int:
    """
    Clean up stale sessions older than max_age_seconds.
    Note: With TTL-based expiration, Redis handles this automatically.
    This function is for manual cleanup if needed.
    
    Args:
        max_age_seconds: Maximum age for sessions (default: 300 = 5 minutes)
    
    Returns:
        Number of sessions cleaned up
    
    Note:
        Since we use EXPIRE, Redis automatically removes expired keys.
        This function is mainly for logging and monitoring purposes.
    """
    try:
        redis = await get_redis_engine()
        pattern = f"{CacheKeys.LIVE_MAP_SESSION_DATA}:*"
        
        # Scan for all session keys
        keys = []
        async for key in redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        
        logger.info(f"Found {len(keys)} active sessions")
        
        # Redis TTL handles expiration automatically
        # This is just for monitoring
        return 0
        
    except Exception as e:
        logger.error(f"Error during stale session cleanup: {e}")
        return 0

