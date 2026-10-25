import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from typing import AsyncGenerator
from utils.async_log import get_logger
from utils.azure_vault import vault_client

logger = get_logger("database")

# Load environment variables from .env file
load_dotenv()

# Check if running on local machine
AT_LOCAL_MACHINE = os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes')

if AT_LOCAL_MACHINE:
    logger.info("Running at local machine - using local database credentials")
    from utils.local_credentials import get_local_credentials, build_database_url, log_local_usage
    
    # Get local credentials
    local_creds = get_local_credentials('database')
    log_local_usage('database')
    
    # Set variables from local credentials
    DB_NAME = local_creds['database']
    DB_USER = local_creds['username']
    DB_PASSWORD = local_creds['password']
    DB_HOST = local_creds['host']
    DB_PORT = str(local_creds['port'])
    DB_ECHO = local_creds['echo']
    DATABASE_URL = build_database_url(local_creds)
    
else:
    # Production environment - use environment variables and Azure Key Vault
    
    # Helper to get Azure Key Vault password synchronously
    def get_azure_password():
        try:
            # Create a new event loop for this thread
            import asyncio
            try:
                # Try to get existing loop first
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, we need a new one
                    import threading
                    import concurrent.futures
                    
                    def get_password():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(vault_client.get_database_password())
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(get_password)
                        return future.result(timeout=30)
                else:
                    # No running loop, we can use run_until_complete
                    return loop.run_until_complete(vault_client.get_database_password())
            except RuntimeError:
                # No event loop in this thread, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(vault_client.get_database_password())
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"Failed to get password from Azure Key Vault: {e}")
            return os.getenv('USER_PASS', 'postgres')

    # Database config from environment or Azure Key Vault
    DB_NAME = os.getenv('DB_NAME', 'sentinelflux')
    DB_USER = os.getenv('USERNAME', 'postgres')
    DB_PASSWORD = get_azure_password()
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_ECHO = os.getenv('DB_ECHO', 'False').lower() in ('true', '1', 'yes')

    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Database connection configured for {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=DB_ECHO, future=True)

# Create sessionmaker for async sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base for models
Base = declarative_base()

# Dependency for FastAPI endpoints (async)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# Export the sessionmaker for use in other modules
async_session_factory = AsyncSessionLocal