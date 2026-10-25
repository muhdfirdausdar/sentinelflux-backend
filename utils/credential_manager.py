"""
Centralized credential management for SentinelFlux
Handles environment-aware credential fetching with Azure Key Vault integration
"""

import os
from typing import Dict, Any, Optional
from utils.async_log import get_logger

logger = get_logger("credential_manager")

# Check if running on local machine
AT_LOCAL_MACHINE = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')

class CredentialManager:
    """Centralized credential management with environment awareness"""
    
    @staticmethod
    async def get_database_credentials() -> Dict[str, Any]:
        """Get database credentials based on environment"""
        if AT_LOCAL_MACHINE:
            from utils.local_credentials import get_local_credentials, log_local_usage
            creds = get_local_credentials('database')
            log_local_usage('database')
            return {
                'host': creds['host'],
                'port': creds['port'],
                'database': creds['database'],
                'username': creds['username'],
                'password': creds['password'],
                'echo': creds['echo'],
                'source': 'local_credentials'
            }
        else:
            from utils.azure_vault import vault_client
            try:
                password = await vault_client.get_database_password()
                return {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': int(os.getenv('DB_PORT', 5432)),
                    'database': os.getenv('DB_NAME', 'sentinelflux'),
                    'username': os.getenv('USERNAME', 'postgres'),
                    'password': password,
                    'echo': os.getenv('DB_ECHO', 'False').lower() in ('true', '1', 'yes'),
                    'source': 'azure_vault'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get database credentials from vault: {e}")
                return {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': int(os.getenv('DB_PORT', 5432)),
                    'database': os.getenv('DB_NAME', 'sentinelflux'),
                    'username': os.getenv('USERNAME', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', ''),
                    'echo': os.getenv('DB_ECHO', 'False').lower() in ('true', '1', 'yes'),
                    'source': 'environment_fallback'
                }
    
    @staticmethod
    async def get_redis_credentials() -> Dict[str, Any]:
        """Get Redis credentials based on environment"""
        if AT_LOCAL_MACHINE:
            from utils.local_credentials import get_local_credentials, log_local_usage
            creds = get_local_credentials('redis')
            log_local_usage('redis')
            return {
                'host': creds['host'],
                'port': creds['port'],
                'database': creds['database'],
                'username': creds['username'],
                'password': creds['password'],
                'source': 'local_credentials'
            }
        else:
            from utils.azure_vault import vault_client
            try:
                password = await vault_client.get_redis_password()
                return {
                    'host': os.getenv('REDIS_HOST', os.getenv('DB_HOST', 'localhost')),
                    'port': int(os.getenv('REDIS_PORT', 6379)),
                    'database': int(os.getenv('REDIS_DB', 0)),
                    'username': os.getenv('REDIS_USERNAME', None),
                    'password': password,
                    'source': 'azure_vault'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get Redis credentials from vault: {e}")
                return {
                    'host': os.getenv('REDIS_HOST', os.getenv('DB_HOST', 'localhost')),
                    'port': int(os.getenv('REDIS_PORT', 6379)),
                    'database': int(os.getenv('REDIS_DB', 0)),
                    'username': os.getenv('REDIS_USERNAME', None),
                    'password': os.getenv('REDIS_PASSWORD', ''),
                    'source': 'environment_fallback'
                }
    
    @staticmethod
    async def get_dnflux_credentials() -> Dict[str, Any]:
        """Get DNFlux credentials based on environment"""
        if AT_LOCAL_MACHINE:
            from utils.local_credentials import get_local_credentials, log_local_usage
            creds = get_local_credentials('dnflux')
            log_local_usage('dnflux')
            return {
                'base_url': creds['base_url'],
                'api_token': creds['api_token'],
                'source': 'local_credentials'
            }
        else:
            from utils.azure_vault import vault_client
            try:
                api_token = await vault_client.get_dnflux_apikey()
                if not api_token:
                    # Fallback to environment variable
                    api_token = os.getenv('DNFLUX_INTERNAL_TOKEN', '')
                    logger.warning("⚠️ Using fallback DNFlux API token from environment")
                
                base_url = os.getenv('DNFLUX_VM2_URL', '')
                
                return {
                    'base_url': base_url,
                    'api_token': api_token,
                    'source': 'azure_vault'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get DNFlux credentials from vault: {e}")
                # Fallback to environment variables
                return {
                    'base_url': os.getenv('DNFLUX_VM2_URL', ''),
                    'api_token': os.getenv('DNFLUX_INTERNAL_TOKEN', ''),
                    'source': 'environment_fallback'
                }
    
    @staticmethod
    async def get_sentinelflux_api_key() -> Dict[str, Any]:
        """Get SentinelFlux API key based on environment, using Redis as a 10-minute buffer."""
        if AT_LOCAL_MACHINE:
            from utils.local_credentials import get_local_credentials
            try:
                creds = get_local_credentials('api_key')
                return {
                    'api_key': creds['sentinelflux_api_key'],
                    'source': 'local_credentials'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get local API key: {e}")
                return {
                    'api_key': os.getenv("API_KEY", ""),
                    'source': 'environment_fallback'
                }

        else:
            from utils.azure_vault import vault_client
            from utils.cache_keys import CacheKeys, CacheTTL
            from redis_client import get_redis_engine
            try:
                redis_client = await get_redis_engine()
                cache_key = CacheKeys.DNFLUX_APIKEY
                cached_api_key = await redis_client.get(cache_key)
                if cached_api_key:
                    return {
                        'api_key': cached_api_key,
                        'source': 'redis_cache'
                    }
                # Not in cache, fetch from vault
                api_key = await vault_client.get_api_key()
                if not api_key:
                    api_key = os.getenv("API_KEY", "")
                    logger.warning("⚠️ Using fallback API key from environment")
                # Store in Redis for 10 minutes (600 seconds)
                await redis_client.set(cache_key, api_key, ex=600)
                return {
                    'api_key': api_key,
                    'source': 'azure_vault' if api_key != os.getenv("API_KEY", "") else 'environment_fallback'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get API key from vault or cache: {e}")
                return {
                    'api_key': os.getenv("API_KEY", ""),
                    'source': 'environment_fallback'
                }

    @staticmethod
    async def get_brevo_api_key() -> Dict[str, Any]:
        """Get Brevo API key based on environment.

        Local machine: read from `utils.local_credentials` (placeholder)
        Production: read from Azure Key Vault secret `brevo-api-key` with
        environment fallback `BREVO_API`.
        """
        if AT_LOCAL_MACHINE:
            from utils.local_credentials import get_local_brevo_api_key, log_local_usage
            try:
                key = get_local_brevo_api_key()
                log_local_usage('brevo_api')
                return {
                    'brevo_api': key,
                    'source': 'local_credentials'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get local Brevo API key: {e}")
                return {
                    'brevo_api': os.getenv('BREVO_API', ''),
                    'source': 'environment_fallback'
                }
        else:
            from utils.azure_vault import vault_client
            try:
                api_key = await vault_client.get_brevo_api_key()
                if not api_key:
                    api_key = os.getenv('BREVO_API', '')
                    logger.warning("⚠️ Using fallback Brevo API key from environment")
                return {
                    'brevo_api': api_key,
                    'source': 'azure_vault' if api_key != os.getenv('BREVO_API', '') else 'environment_fallback'
                }
            except Exception as e:
                logger.error(f"❌ Failed to get Brevo API key from vault: {e}")
                return {
                    'brevo_api': os.getenv('BREVO_API', ''),
                    'source': 'environment_fallback'
                }

# Global instance
credential_manager = CredentialManager()
