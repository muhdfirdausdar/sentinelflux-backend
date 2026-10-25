import os
from redis.asyncio import Redis
from utils.async_log import get_logger
from utils.azure_vault import vault_client
from dotenv import load_dotenv

logger = get_logger("redis")

# Load environment variables from .env file
load_dotenv()

# Check if running on local machine
AT_LOCAL_MACHINE = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')

if AT_LOCAL_MACHINE:
    logger.info("Running at local machine - using local Redis credentials")
    from utils.local_credentials import get_local_credentials, log_local_usage
    
    # Get local credentials
    local_creds = get_local_credentials('redis')
    log_local_usage('redis')
    
    # Set variables from local credentials
    REDIS_HOST = local_creds['host']
    REDIS_PORT = local_creds['port']
    REDIS_DB = local_creds['database']
    REDIS_USERNAME = local_creds['username']
    REDIS_LOCAL_PASSWORD = local_creds['password']
    
else:
    # Production environment - use environment variables and Azure Key Vault
    REDIS_HOST = os.getenv('REDIS_HOST', os.getenv('DB_HOST', 'localhost'))
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_USERNAME = os.getenv('REDIS_USERNAME', None)
    REDIS_LOCAL_PASSWORD = None

    logger.info(f"Production Redis settings - Host: {REDIS_HOST}:{REDIS_PORT}")

# Global Redis engine (connection pool)
_redis_engine = None

async def get_redis_password():
    """Get Redis password from Azure Key Vault"""
    return await vault_client.get_redis_password()

async def get_redis_engine():
    """Get or create Redis connection pool"""
    global _redis_engine
    
    if _redis_engine is None:
        if AT_LOCAL_MACHINE:
            # Use local credentials
            password = REDIS_LOCAL_PASSWORD
        else:
            # Use Azure Key Vault
            password = await get_redis_password()
        
        _redis_engine = Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            username=REDIS_USERNAME,
            password=password,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
        logger.info(f"Redis engine created: {REDIS_USERNAME}@{REDIS_HOST}:{REDIS_PORT}")
    
    return _redis_engine

# Legacy compatibility - for backward compatibility with existing code
redis = None

async def init_redis():
    """Initialize Redis engine"""
    global redis
    redis = await get_redis_engine()
    logger.info("Redis initialized successfully")

# Dependency for FastAPI endpoints
async def get_redis():
    """Get Redis connection for FastAPI endpoints"""
    return await get_redis_engine()
