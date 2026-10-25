"""
Connection testing utilities for SentinelFlux
"""
import os
import socket
from sqlalchemy import text
from utils.async_log import get_logger

logger = get_logger("connection_test")


import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from redis.asyncio import Redis
from typing import Dict
from utils.async_log import get_logger

logger = get_logger("connection_test")

async def test_database_connection(engine: AsyncEngine) -> bool:
    """Test database connection"""
    try:
        logger.info("🔍 Testing database connection...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

async def test_redis_connection(redis_client: Redis) -> bool:
    """Test Redis connection"""
    try:
        logger.info("🔍 Testing Redis connection...")
        await redis_client.ping()
        
        # Test basic operations
        test_key = "connection_test"
        await redis_client.set(test_key, "test_value", ex=10)
        value = await redis_client.get(test_key)
        await redis_client.delete(test_key)
        
        if value == "test_value":
            logger.info("✅ Redis connection successful")
            return True
        else:
            logger.error("❌ Redis operation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False

async def test_dnflux_vm2_connection(dnflux_pool=None) -> bool:
    """Test DNFlux VM2 connection using provided initialized pool"""
    try:
        logger.info("🔍 Testing DNFlux VM2 connection...")
        
        # Use provided pool or import global pool
        if dnflux_pool is None:
            from dnflux_pool import dnflux_pool as global_pool
            dnflux_pool = global_pool
        
        # Check if pool is initialized
        if not dnflux_pool.is_initialized():
            logger.error("❌ DNFlux pool not initialized")
            return False
        
        # Use the initialized pool with proper headers (X-API-Key) to test connection
        logger.info(f"🌐 Testing connection to: {dnflux_pool.base_url}")
        response = await dnflux_pool.request_with_retry("GET", "/")
        
        if response.status_code == 200:
            logger.info("✅ DNFlux VM2 connection successful")
            logger.info(f"📊 Pool stats: {dnflux_pool.get_connection_stats()}")
            return True
        else:
            logger.error(f"❌ DNFlux VM2 returned status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ DNFlux VM2 connection failed: {e}")
        return False

async def test_all_connections(db_engine: AsyncEngine, redis_client: Redis, dnflux_pool=None) -> Dict[str, bool]:
    """
    Test all critical connections
    
    Args:
        db_engine: Database engine
        redis_client: Redis client
        dnflux_pool: Optional initialized DNFlux pool (from app.state)
        
    Returns:
        Dict mapping connection names to success status
    """
    logger.info("🚀 Starting critical connection tests...")
    
    # Run all tests concurrently
    tasks = {
        'database': test_database_connection(db_engine),
        'redis': test_redis_connection(redis_client),
        'dnflux_vm2': test_dnflux_vm2_connection(dnflux_pool)
    }
    
    results = {}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as e:
            logger.error(f"❌ Connection test '{name}' failed with exception: {e}")
            results[name] = False
    
    # Log summary
    passed = sum(results.values())
    total = len(results)
    
    logger.info(f"📊 Connection test summary: {passed}/{total} passed")
    
    for name, status in results.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"  {status_icon} {name}: {'PASS' if status else 'FAIL'}")
    
    return results


async def test_database_functionality(engine):
    """Test basic database functionality"""
    try:
        logger.info("🔍 Testing database functionality...")
        
        # Test basic queries
        async with engine.begin() as conn:
            # Test basic query
            result = await conn.execute(text("SELECT current_database(), version()"))
            db_info = result.fetchone()
            logger.info(f"📝 Connected to database: {db_info[0]}")
            logger.info(f"📝 PostgreSQL version: {db_info[1][:50]}...")
            
            # Test if main tables exist
            table_checks = [
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'domain')",
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ips')",
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'nameserver')"
            ]
            
            for i, check in enumerate(table_checks):
                result = await conn.execute(text(check))
                exists = result.scalar()
                table_name = ['domain', 'ips', 'nameserver'][i]
                if exists:
                    logger.info(f"✅ Table '{table_name}' exists")
                else:
                    logger.warning(f"⚠️ Table '{table_name}' does not exist")
                    
        return True
    except Exception as e:
        logger.error(f"❌ Database functionality test failed: {str(e)}")
        return False
