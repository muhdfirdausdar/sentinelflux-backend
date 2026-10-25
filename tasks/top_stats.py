"""
Top Stats Task

Runs as background task to fetch top stats every 2 minutes
Use local redis cache to store the fetched stats

"""

import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from utils.async_log import get_logger
from dnflux_pool import dnflux_pool
from utils.cache_keys import CacheKeys
from sqlalchemy import text


logger = get_logger("top_stats_task")

# Configurable interval (seconds)
def parse_int_env(key, default):
    val = os.getenv(key, str(default))
    try:
        return int(val.strip().split()[0])
    except Exception:
        return int(default)


TOP_STATS_FETCH_INTERVAL = parse_int_env("TOP_STATS_FETCH_INTERVAL", 120)  # 2 minutes default

class TopStatsFetcher:
    """
    Class to fetch top stats from DNFlux VM2 and store in Redis cache
    """

    def __init__(self):
        pass

    # Create and handle many queries to database

    async def query_top_stats(self, session) -> Optional[Dict[str, Any]]:
        """
        Query top stats from database
        Returns a dictionary of top stats
        
        Args:
            session: AsyncSession database session

        return structure:
        {
            "top10_geoip":
                {
                    "1": {"longitude": 101.6869, "latitude": 3.139, "country": "Malaysia"},
                    "2": {"longitude": 101.6869, "latitude": 3.139, "country": "Malaysia"},
                    "3": {"longitude": 13.4050, "latitude": 52.5200, "country": "Germany"},
                    "4": {"longitude": 2.3522, "latitude": 48.8566, "country": "France"},
                    "5": {"longitude": -0.1276, "latitude": 51.5074, "country": "UK"},
                    "6": {"longitude": -75.6972, "latitude": 45.4215, "country": "Canada"},
                    "7": {"longitude": 151.2093, "latitude": -33.8688, "country": "Australia"},
                    "8": {"longitude": -47.9292, "latitude": -15.7801, "country": "Brazil"},
                    "9": {"longitude": 78.9629, "latitude": 20.5937, "country": "India"},
                    "10": {"longitude": 138.2529, "latitude": 36.2048, "country": "Japan"}
                },
            "top10_ips":
                {
                    "1": "192.168.1.1",
                    "2": "192.168.1.2",
                    "3": "192.168.1.3",
                    "4": "192.168.1.4",
                    "5": "192.168.1.5",
                    "6": "192.168.1.6",
                    "7": "192.168.1.7",
                    "8": "192.168.1.8",
                    "9": "192.168.1.9",
                    "10": "192.168.1.10"
                },
            "top10_nameserver":
                {
                    "1": "ns1.example.com",
                    "2": "ns2.example.com",
                    "3": "ns3.example.com",
                    "4": "ns4.example.com",
                    "5": "ns5.example.com",
                    "6": "ns6.example.com",
                    "7": "ns7.example.com",
                    "8": "ns8.example.com",
                    "9": "ns9.example.com",
                    "10": "ns10.example.com"
                }
            }

        """
        try:
            # Query 1: Get all domain IDs that have fast flux (flux_type NOT 'unknown')
            fast_flux_domain_ids_query = text("""
                SELECT DISTINCT domain_id 
                FROM fast_flux_analysis 
                WHERE flux_type != 'unknown'
            """)
            result = await session.execute(fast_flux_domain_ids_query)
            fast_flux_domain_ids = [row[0] for row in result.fetchall()]
            
            # Query 1b: Get domain IDs that have name flux specifically (for nameserver stats)
            name_flux_domain_ids_query = text("""
                SELECT DISTINCT domain_id 
                FROM fast_flux_analysis 
                WHERE flux_type = 'name'
            """)
            result = await session.execute(name_flux_domain_ids_query)
            name_flux_domain_ids = [row[0] for row in result.fetchall()]
            
            if not fast_flux_domain_ids:
                logger.warning("⚠️ No fast flux domains found")
                return {
                    "top10_geoip": {},
                    "top10_ips": {},
                    "top10_nameserver": {}
                }
            
            # Use name flux domains for nameserver stats, fall back to all fast flux if none found
            if not name_flux_domain_ids:
                logger.warning("⚠️ No name flux domains found, using all fast flux domains for nameserver stats")
                nameserver_domain_ids = fast_flux_domain_ids
            else:
                nameserver_domain_ids = name_flux_domain_ids
            
            # Query 2: Top 10 GeoIP countries (by IP count) with lat/long
            # Get all IPs related to fast flux domains, then count by country
            # Also get one representative latitude_longitude for each country
            top_geoip_query = text("""
                SELECT 
                    ig.country, 
                    COUNT(DISTINCT dic.ip_id) as ip_count,
                    MIN(ig.latitude_longitude) as lat_long
                FROM domain_ip_connection dic
                INNER JOIN ip_geolocation ig ON dic.ip_id = ig.ip_id
                WHERE dic.domain_id = ANY(:domain_ids)
                GROUP BY ig.country
                ORDER BY ip_count DESC
                LIMIT 10
            """)
            result = await session.execute(top_geoip_query, {"domain_ids": fast_flux_domain_ids})
            top_geoip_rows = result.fetchall()
            
            # Query 3: Top 10 IP addresses (by mention count in domain_ip_connection)
            top_ips_query = text("""
                SELECT i.ip_address, COUNT(dic.id) as mention_count
                FROM domain_ip_connection dic
                INNER JOIN ips i ON dic.ip_id = i.id
                WHERE dic.domain_id = ANY(:domain_ids)
                GROUP BY dic.ip_id, i.ip_address
                ORDER BY mention_count DESC
                LIMIT 10
            """)
            result = await session.execute(top_ips_query, {"domain_ids": fast_flux_domain_ids})
            top_ips_rows = result.fetchall()
            
            # Query 4: Top 10 Nameservers (by mention count in domain_nameserver)
            # Prefer domains with flux_type = 'name', fall back to all fast flux if none
            # Exclude nameservers that match or are subdomains of domains in domain_filter
            # Use RIGHT() to check if nameserver ends with the filtered domain
            # Convert nameserver to lowercase for consistent display
            top_nameserver_query = text("""
                SELECT LOWER(ns.nameserver) as nameserver, COUNT(dns.id) as mention_count
                FROM domain_nameserver dns
                INNER JOIN nameserver ns ON dns.nameserver_id = ns.id
                WHERE dns.domain_id = ANY(:domain_ids)
                  AND NOT EXISTS (
                    SELECT 1 
                    FROM domain_filter df
                    WHERE LOWER(ns.nameserver) = LOWER(df.domain_name)
                       OR RIGHT(LOWER(ns.nameserver), LENGTH(df.domain_name) + 1) = ('.' || LOWER(df.domain_name))
                  )
                GROUP BY LOWER(ns.nameserver)
                ORDER BY mention_count DESC
                LIMIT 10
            """)
            result = await session.execute(top_nameserver_query, {"domain_ids": nameserver_domain_ids})
            top_nameserver_rows = result.fetchall()
            
            # Format the results
            # Parse GeoIP data with latitude and longitude
            top10_geoip = {}
            for i, row in enumerate(top_geoip_rows):
                country = row[0]
                lat_long_str = row[2]  # latitude_longitude column
                
                # Parse latitude_longitude string (format: "latitude, longitude")
                try:
                    if lat_long_str and ',' in lat_long_str:
                        parts = lat_long_str.split(',')
                        latitude = float(parts[0].strip())
                        longitude = float(parts[1].strip())
                    else:
                        # Default values if parsing fails
                        latitude = 0.0
                        longitude = 0.0
                        logger.warning(f"Invalid lat_long format for {country}: {lat_long_str}")
                except (ValueError, IndexError) as e:
                    latitude = 0.0
                    longitude = 0.0
                    logger.warning(f"Failed to parse lat_long for {country}: {e}")
                
                top10_geoip[str(i+1)] = {
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude
                }
            
            top10_ips = {str(i+1): str(row[0]) for i, row in enumerate(top_ips_rows)}
            top10_nameserver = {str(i+1): row[0] for i, row in enumerate(top_nameserver_rows)}
            
            logger.debug(f"✅ Successfully queried top stats: {len(top10_geoip)} geoip, {len(top10_ips)} IPs, {len(top10_nameserver)} nameservers")
            
            return {
                "top10_geoip": top10_geoip,
                "top10_ips": top10_ips,
                "top10_nameserver": top10_nameserver
            }
                
        except Exception as e:
            logger.error(f"❌ Failed to query top stats: {e}")
            import traceback
            logger.error(f"Top stats query traceback: {traceback.format_exc()}")
            return None

    async def update_redis_cache(self) -> bool:
        """
        Fetch top stats from database and update Redis cache
        
        Returns:
            bool: True if successfully updated cache, False otherwise
        """
        try:
            # Get database and redis instances
            from database import AsyncSessionLocal
            from redis_client import get_redis_engine
            
            redis = await get_redis_engine()
            
            # Query top stats from database using session
            logger.debug("🔄 Querying top stats from database...")
            async with AsyncSessionLocal() as db_session:
                stats_data = await self.query_top_stats(db_session)
            
            if stats_data is None:
                logger.error("❌ Failed to query top stats, cannot update Redis cache")
                return False
            
            # Get current timestamp in ISO format
            current_time = datetime.utcnow().isoformat()
            
            # Prepare Redis hash data
            cache_key = CacheKeys.PREFETCHED_TOP_STATS
            redis_data = {
                "last_update": current_time,
                "data": json.dumps(stats_data)
            }
            
            # Delete old cache if exists and create new one
            async with redis.pipeline() as pipe:
                await pipe.delete(cache_key)
                await pipe.hset(cache_key, mapping=redis_data)
                await pipe.execute()
            
            logger.debug(f"✅ Successfully updated Redis cache at {current_time}")
            logger.debug(f"📊 Cache stats: {len(stats_data.get('top10_geoip', {}))} geoip, "
                        f"{len(stats_data.get('top10_ips', {}))} IPs, "
                        f"{len(stats_data.get('top10_nameserver', {}))} nameservers")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update Redis cache: {e}")
            import traceback
            logger.error(f"Redis cache update traceback: {traceback.format_exc()}")
            return False

    async def get_top_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get top stats from Redis cache
        
        Returns:
            dict: Dictionary with 'last_update' and 'data' fields if cache exists
            None: If cache doesn't exist or error occurs
            
        Example return:
        {
            "last_update": "2025-10-26T12:34:56.789012",
            "data": {
                "top10_geoip": {...},
                "top10_ips": {...},
                "top10_nameserver": {...}
            }
        }
        """
        try:
            # Get redis instance
            from redis_client import get_redis_engine
            
            redis = await get_redis_engine()
            
            cache_key = CacheKeys.PREFETCHED_TOP_STATS
            
            # Check if key exists
            exists = await redis.exists(cache_key)
            if not exists:
                logger.warning("⚠️ Top stats cache does not exist")
                return None
            
            # Get all hash fields
            cached_data = await redis.hgetall(cache_key)
            
            if not cached_data or not cached_data.get("last_update") or not cached_data.get("data"):
                logger.warning("⚠️ Top stats cache exists but is incomplete")
                return None
            
            # Parse the JSON data
            try:
                stats_data = json.loads(cached_data["data"])
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse cached stats data: {e}")
                return None
            
            result = {
                "last_update": cached_data["last_update"],
                "data": stats_data
            }
            
            logger.debug(f"✅ Retrieved top stats from cache, last updated: {cached_data['last_update']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get top stats from Redis: {e}")
            import traceback
            logger.error(f"Get top stats traceback: {traceback.format_exc()}")
            return None


async def top_stats_loop():
    """
    Main loop that fetches and updates top stats every TOP_STATS_FETCH_INTERVAL seconds
    """
    logger.info(f"🚀 Starting top stats fetcher loop (interval: {TOP_STATS_FETCH_INTERVAL}s)...")
    logger.info(f"📦 Redis cache key: {CacheKeys.PREFETCHED_TOP_STATS}")
    
    fetcher = TopStatsFetcher()
    loop_count = 0
    last_success_time = None
    consecutive_failures = 0

    while True:
        loop_count += 1
        loop_start_time = time.time()
        
        logger.debug(f"📈 Top stats loop #{loop_count} starting...")
        
        try:
            # Update Redis cache with latest top stats
            success = await fetcher.update_redis_cache()
            
            if success:
                last_success_time = datetime.utcnow().isoformat()
                consecutive_failures = 0
                loop_duration = time.time() - loop_start_time
                logger.info(f"✅ Successfully update top stats")
            else:
                consecutive_failures += 1
                logger.warning(f"⚠️ Loop #{loop_count} failed to update cache (consecutive failures: {consecutive_failures})")
                
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"❌ Exception in top stats loop #{loop_count}: {e}")
            import traceback
            logger.error(f"Top stats loop traceback: {traceback.format_exc()}")
        
        # Log status summary periodically
        if loop_count % 10 == 0:  # Every 10 loops
            logger.debug(f"📊 Loop #{loop_count} status summary:")
            logger.debug(f"  ⏰ Last success: {last_success_time or 'Never'}")
            logger.debug(f"  ❌ Consecutive failures: {consecutive_failures}")
            logger.debug(f"  🔄 Total loops: {loop_count}")
        
        logger.debug(f"😴 Top stats loop #{loop_count} sleeping for {TOP_STATS_FETCH_INTERVAL} seconds...")
        
        try:
            await asyncio.sleep(TOP_STATS_FETCH_INTERVAL)
        except Exception as e:
            logger.error(f"❌ Exception during sleep in loop #{loop_count}: {e}")
        
        logger.debug(f"⏰ Top stats loop #{loop_count} woke up from sleep")


# Export the main functions
__all__ = ["top_stats_loop", "TopStatsFetcher"]
