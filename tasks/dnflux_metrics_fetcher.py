"""
DNFlux Metrics Fetcher Task

This module runs as a background task to fetch /helper/metrics 
from DNFlux VM2 every 30 seconds using the global dnflux_pool
and saves the metrics to Redis buffer.
"""

import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from utils.async_log import get_logger
from utils.cache_keys import CacheKeys, CacheTTL
from dnflux_pool import dnflux_pool
from redis_client import get_redis_engine

logger = get_logger("dnflux_metrics_fetcher")

# Configurable interval (seconds)
def parse_int_env(key, default):
    val = os.getenv(key, str(default))
    try:
        return int(val.strip().split()[0])
    except Exception:
        return int(default)

DNFLUX_FETCH_INTERVAL = parse_int_env("DNFLUX_FETCH_INTERVAL", 30)  # 30 seconds default

async def fetch_dnflux_metrics():
    """
    Fetch /helper/metrics from DNFlux VM2 using the global pool
    and save to Redis buffer with proper error handling
    """
    try:
        logger.debug("🔍 Fetching DNFlux metrics from /helper/metrics...")
        
        # Fetch metrics from DNFlux VM2 (request_with_retry handles connection issues)
        response = await dnflux_pool.request_with_retry("GET", "/helper/metrics")
        
        if response.status_code == 200:
            # Parse the JSON response
            metrics_data = response.json()
            
            # Add fetch timestamp
            fetch_timestamp = datetime.utcnow().isoformat()
            metrics_data["fetch_timestamp"] = fetch_timestamp
            metrics_data["source"] = "dnflux_vm2"
            
            logger.info(f"✅ Successfully fetched DNFlux metrics (timestamp: {fetch_timestamp})")
            logger.debug(f"📊 Metrics data: {json.dumps(metrics_data, indent=2)}")
            
            # Save to Redis buffer
            await save_metrics_to_redis(metrics_data)
            
        elif response.status_code == 404:
            logger.warning("⚠️ DNFlux metrics endpoint returned 404 - No metrics available")
        elif response.status_code == 503:
            logger.warning("⚠️ DNFlux metrics service not available (503)")
        else:
            logger.error(f"❌ DNFlux metrics fetch failed with status {response.status_code}")
            logger.error(f"Response content: {response.text}")
        
    except Exception as e:
        logger.error(f"❌ Error fetching DNFlux metrics: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def save_metrics_to_redis(metrics_data: dict):
    """Save the latest metrics to Redis buffer, overwriting previous data"""
    try:
        redis_client = await get_redis_engine()
        
        # Add timestamp to the metrics data
        metrics_with_timestamp = {
            **metrics_data,
            "buffer_timestamp": datetime.now().isoformat()
        }
        
        # Store only the latest metrics (overwrite previous)
        await redis_client.set(
            CacheKeys.DNFLUX_METRICS_BUFFER,
            json.dumps(metrics_with_timestamp),
            ex=3600  # Expire in 1 hour as failsafe
        )
        
        logger.debug(f"✅ Saved latest DNFlux metrics to Redis buffer")
        
    except Exception as e:
        logger.error(f"❌ Failed to save metrics to Redis: {str(e)}")
        raise

async def get_latest_metrics_from_buffer() -> Optional[Dict[str, Any]]:
    """
    Get the latest metrics from Redis buffer
    
    Returns:
        Latest metrics data or None if not available
    """
    try:
        redis_client = await get_redis_engine()
        latest_key = CacheKeys.DNFLUX_METRICS_BUFFER
        
        data = await redis_client.get(latest_key)
        if data:
            return json.loads(data)
        return None
        
    except Exception as e:
        logger.error(f"❌ Error retrieving metrics from buffer: {e}")
        return None

async def dnflux_metrics_loop():
    """
    Main loop that fetches DNFlux metrics every DNFLUX_FETCH_INTERVAL seconds
    """
    logger.info(f"🚀 Starting DNFlux metrics fetcher loop (interval: {DNFLUX_FETCH_INTERVAL}s)...")
    logger.info("🎯 Target endpoint: /helper/metrics")
    logger.info(f"📦 Redis buffer key: {CacheKeys.DNFLUX_METRICS_BUFFER}")
    
    loop_count = 0
    last_success_time = None
    consecutive_failures = 0
    do_reset = False

    while True:
        loop_count += 1
        loop_start_time = time.time()
        
        logger.debug(f"📈 DNFlux metrics loop #{loop_count} starting...")
        
        try:
            # Check if dnflux_pool is initialized and healthy
            if not dnflux_pool.is_initialized():
                logger.warning("⚠️ DNFlux pool not initialized - attempting to reset...")
                do_reset = True
                consecutive_failures += 1
            elif not dnflux_pool.is_healthy():
                logger.warning("⚠️ DNFlux pool not healthy - attempting to reset...")
                do_reset = True
                consecutive_failures += 1
            else:
                do_reset = False
            
            if do_reset:
                # Attempt to reset the pool
                try:
                    await dnflux_pool.reset_connection()
                    logger.info("🔄 DNFlux pool reset completed. Will verify on next loop.")
                    # Don't set do_reset = False here - let next iteration check health
                except Exception as e:
                    logger.error(f"❌ Failed to reset DNFlux pool: {e}")
            else:
                # Pool is healthy - fetch metrics
                try:
                    await fetch_dnflux_metrics()
                    # Track success
                    last_success_time = datetime.utcnow().isoformat()
                    consecutive_failures = 0
                    
                    loop_duration = time.time() - loop_start_time
                    logger.debug(f"✅ Loop #{loop_count} completed successfully in {loop_duration:.2f}s")
                except Exception as fetch_error:
                    logger.error(f"❌ Failed to fetch metrics: {fetch_error}")
                    consecutive_failures += 1
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"❌ Exception in DNFlux metrics loop #{loop_count}: {e}")
            import traceback
            traceback.print_exc()
        
        # Log status summary periodically
        if loop_count % 10 == 0:  # Every 10 loops
            logger.debug(f"📊 Loop #{loop_count} status summary:")
            logger.debug(f"  ⏰ Last success: {last_success_time or 'Never'}")
            logger.debug(f"  ❌ Consecutive failures: {consecutive_failures}")
            logger.debug(f"  🔄 Total loops: {loop_count}")
        
        logger.debug(f"😴 DNFlux metrics loop #{loop_count} sleeping for {DNFLUX_FETCH_INTERVAL} seconds...")
        
        try:
            await asyncio.sleep(DNFLUX_FETCH_INTERVAL)
        except Exception as e:
            logger.error(f"❌ Exception during sleep in loop #{loop_count}: {e}")
        
        logger.debug(f"⏰ DNFlux metrics loop #{loop_count} woke up from sleep")

# Export the main functions
__all__ = ["dnflux_metrics_loop", "get_latest_metrics_from_buffer"]
