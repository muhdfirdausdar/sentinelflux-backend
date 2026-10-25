"""
Redis Cache Keys Management Module

This module centralizes all Redis cache keys used across the application
to avoid key conflicts and provide better documentation.
"""

from typing import Dict, Any
from enum import Enum
from utils.async_log import get_logger

logger = get_logger("redis_keys")

class CacheKeys:
    """
    Centralized Redis cache keys management
    
    Usage:
        key = CacheKeys.VM2_DATA.format(param="value")
        key = CacheKeys.DOMAIN_DETAILS(domain_id=123)
    """
    
    # Inter-VM communication cache keys
    VM2_DATA = "vm2:data"
    VM2_METADATA = "vm2:metadata"
    VM2_METRICS = "vm2:metrics:{timestamp}"
    DNFLUX_APIKEY = "dnflux:apikey"  # API key buffering
    DNFLUX_METRICS_BUFFER = "buffer:dnflux:metrics"  # Latest DNFlux metrics buffer
    
    # Domain-related cache keys
    DOMAIN_DETAILS = "domain:details:{domain_id}"
    DOMAIN_INFO = "domain:id:{domain_id}"
    DOMAIN_VISUALIZATION = "domain:vis:{domain_id}"
    
    # Analysis cache keys
    FASTFLUX_ANALYSIS = "analysis:fastflux:{domain_id}"
    GEOIP_DATA = "geoip:{ip_address}"
    
    # Statistics cache keys
    DB_STATUS = "stats:db_status"
    SYSTEM_METRICS = "stats:system:{timestamp}"
    
    # API rate limiting keys
    RATE_LIMIT = "ratelimit:{client_ip}:{endpoint}"
    
    # Health check keys
    HEALTH_VM2 = "health:vm2"
    HEALTH_DATABASE = "health:database"
    HEALTH_REDIS = "health:redis"

    # Visualize routes keys
    LIVE_MAP_SESSION_DATA = "visualize:live_map"

    PREFETCHED_TOP_STATS = "prefetch:top_stats"

    @classmethod
    def get_domain_details_key(cls, domain_id: int) -> str:
        """Get formatted domain details cache key"""
        return cls.DOMAIN_DETAILS.format(domain_id=domain_id)
    
    @classmethod
    def get_domain_info_key(cls, domain_id: int) -> str:
        """Get formatted domain info cache key"""
        return cls.DOMAIN_INFO.format(domain_id=domain_id)
    
    @classmethod
    def get_geoip_key(cls, ip_address: str) -> str:
        """Get formatted GeoIP cache key"""
        return cls.GEOIP_DATA.format(ip_address=ip_address)
    
    @classmethod
    def get_rate_limit_key(cls, client_ip: str, endpoint: str) -> str:
        """Get formatted rate limit key"""
        return cls.RATE_LIMIT.format(client_ip=client_ip, endpoint=endpoint)
    
    @classmethod
    def get_metrics_key(cls, timestamp: str) -> str:
        """Get formatted metrics cache key"""
        return cls.VM2_METRICS.format(timestamp=timestamp)
    
    @classmethod
    def get_dnflux_apikey_key(cls) -> str:
        """Get DNFlux API key cache key"""
        return cls.DNFLUX_APIKEY

    @classmethod
    def get_live_map_session_key(cls, client_id: str) -> str:
        """Get formatted live map session cache key"""
        return cls.LIVE_MAP_SESSION_DATA.format(client_id=client_id)

class CacheTTL:
    """
    Cache Time-To-Live (TTL) values in seconds
    """
    
    # Short-term cache (1-5 minutes)
    VERY_SHORT = 60        # 1 minute
    SHORT = 300           # 5 minutes
    
    # Medium-term cache (15-60 minutes)
    MEDIUM = 900          # 15 minutes
    LONG = 3600           # 1 hour
    
    # Long-term cache (hours)
    VERY_LONG = 21600     # 6 hours
    DAILY = 86400         # 24 hours
    
    # Specific use cases
    DOMAIN_DETAILS = MEDIUM      # 15 minutes
    VM2_DATA = SHORT            # 5 minutes
    VM2_METADATA = SHORT        # 5 minutes
    GEOIP_DATA = VERY_LONG      # 6 hours (GeoIP data doesn't change often)
    DB_STATUS = SHORT           # 5 minutes
    HEALTH_CHECK = VERY_SHORT   # 1 minute
    DNFLUX_APIKEY = DAILY       # 24 hours (API keys typically last 24h)

class CacheConfig:
    """
    Cache configuration and utilities
    """
    
    @staticmethod
    def get_key_info() -> Dict[str, Any]:
        """Get information about all cache keys"""
        return {
            "vm2_communication": {
                "data": CacheKeys.VM2_DATA,
                "metadata": CacheKeys.VM2_METADATA,
                "metrics": CacheKeys.VM2_METRICS,
                "ttl": CacheTTL.VM2_DATA
            },
            "domain_cache": {
                "details": CacheKeys.DOMAIN_DETAILS,
                "info": CacheKeys.DOMAIN_INFO,
                "visualization": CacheKeys.DOMAIN_VISUALIZATION,
                "ttl": CacheTTL.DOMAIN_DETAILS
            },
            "health_checks": {
                "vm2": CacheKeys.HEALTH_VM2,
                "database": CacheKeys.HEALTH_DATABASE,
                "redis": CacheKeys.HEALTH_REDIS,
                "ttl": CacheTTL.HEALTH_CHECK
            }
        }
    
    @staticmethod
    def log_cache_operation(operation: str, key: str, ttl: int = None):
        """Log cache operations for debugging"""
        if ttl:
            logger.debug(f"Cache {operation}: {key} (TTL: {ttl}s)")
        else:
            logger.debug(f"Cache {operation}: {key}")

# Example usage and testing
if __name__ == "__main__":
    # Test key generation
    domain_id = 123
    ip_address = "192.168.1.1"
    
    print("=== Cache Keys Examples ===")
    print(f"Domain Details: {CacheKeys.get_domain_details_key(domain_id)}")
    print(f"GeoIP Data: {CacheKeys.get_geoip_key(ip_address)}")
    print(f"Rate Limit: {CacheKeys.get_rate_limit_key('127.0.0.1', '/api/domain')}")
    
    print("\n=== Cache Configuration ===")
    config = CacheConfig.get_key_info()
    for category, info in config.items():
        print(f"{category}: {info}")
