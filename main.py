from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, Depends, status, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import get_db
from redis_client import init_redis, get_redis_engine
import os
import asyncio
import traceback
from utils.async_log import get_logger
from utils.connection_test import test_all_connections

from routes.search_domain import router as search_domain_router
from routes.dnflux import router as dnflux_router
from routes.process_status import router as process_status_router
from routes.auth import router as auth_router
from routes.visualize import router as live_map_router
from graphql_api import create_graphql_router

logger = get_logger("main")

# Load environment variables from .env file
load_dotenv()

# Import shared authentication utilities  
from utils.auth import get_api_key, api_key_header, VALID_API_KEY, get_current_user

# Create Limiter instance for global rate limiting
LIMIT_RATE = os.getenv("LIMIT_RATE", "250/minute")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[LIMIT_RATE]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application startup and shutdown"""
    # Startup
    logger.info("🔧 Initializing SentinelFlux backend...")
    
    # Initialize Redis connection
    try:
        await init_redis()
        redis_client = await get_redis_engine()
        logger.info("✅ Redis engine initialized")
        
        # Store Redis client in app state for global access
        app.state.redis_engine = redis_client
        
    except Exception as e:
        logger.error(f"❌ Error initializing Redis: {e}")
        raise RuntimeError("Failed to initialize Redis. Check your Redis configuration.")
    
    # Import database engine and store in app state
    import database
    app.state.db_engine = database.engine
    app.state.async_session_factory = database.AsyncSessionLocal
    
    # Initialize DNFlux global connection pool ONCE
    is_dnflux_initialized = False
    try:
        from dnflux_pool import dnflux_pool
        
        # Initialize the global pool once at startup
        await dnflux_pool.initialize()
        
        # Store global pool in app state for access throughout the app
        app.state.dnflux_pool = dnflux_pool
        
        logger.info("✅ DNFlux global pool initialized")
        logger.info(f"🔗 Global pool ready: {dnflux_pool.base_url}")
        is_dnflux_initialized = True
    except Exception as e:
        logger.error(f"❌ Error initializing DNFlux components: {e}")
        # Don't fail startup for DNFlux components - they're not critical
        logger.warning("⚠️ Continuing startup without DNFlux VM2 connection")
    
    # Test all critical connections before proceeding
    logger.info("🚀 Testing critical connections...")
    
    from utils.connection_test import test_all_connections
    # Pass the initialized dnflux_pool from app.state if available
    dnflux_pool_for_test = app.state.dnflux_pool if is_dnflux_initialized else None
    connection_results = await test_all_connections(database.engine, redis_client, dnflux_pool_for_test)
    
    # Check if critical connections failed
    critical_failures = []
    if not connection_results.get('database', False):
        critical_failures.append('database')
    if not connection_results.get('redis', False):
        critical_failures.append('redis')
    if not connection_results.get('dnflux_vm2', False):
        critical_failures.append('dnflux_vm2')

    # All three connections are critical - fail gracefully if any fail
    if critical_failures:
        error_msg = f"❌ Critical connection failures: {', '.join(critical_failures)}"
        logger.error(error_msg)
        logger.error("🛑 SentinelFlux cannot start without all critical connections. Exiting gracefully...")
        
        # Clean up before exit
        try:
            if hasattr(app.state, 'dnflux_pool'):
                await app.state.dnflux_pool.close()
            if hasattr(app.state, 'redis_engine'):
                await app.state.redis_engine.close()
            await database.engine.dispose()
        except Exception as cleanup_error:
            logger.error(f"⚠️ Error during cleanup: {cleanup_error}")
        
        raise RuntimeError(f"Startup failed - critical connections: {', '.join(critical_failures)}")
    
    logger.info("✅ All critical connections established - SentinelFlux backend ready!")
    
    # Log current process configuration for debugging
    from process_switch import log_process_configuration
    log_process_configuration()
    
    # Start enabled background processes via process switch system
    from process_switch import start_enabled_processes
    await start_enabled_processes(app)
    
    yield
    
    # Stop all enabled processes gracefully
    from process_switch import stop_enabled_processes
    await stop_enabled_processes(app)
    
    # Shutdown
    logger.info("🔌 Shutting down SentinelFlux backend...")
    try:
        # Stop all enabled processes gracefully
        from process_switch import stop_enabled_processes
        await stop_enabled_processes(app)
        
        # Close DNFlux global connection pool
        if hasattr(app.state, 'dnflux_pool'):
            await app.state.dnflux_pool.close()
            logger.info("✅ DNFlux global pool closed")
        
        # Close database connections
        await database.engine.dispose()
        
        # Close Redis connection
        if hasattr(app.state, 'redis_engine'):
            await app.state.redis_engine.close()
        
        logger.info("✅ SentinelFlux backend shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")
        raise

# Create FastAPI app with lifespan
app = FastAPI(
    title="SentinelFlux API",
    description="Fast Flux Detection and Analysis API",
    version="2.0.0",
    lifespan=lifespan
    # Removed global dependencies - each endpoint now handles its own authentication
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware to add security headers - MUST be before routes
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Strict-Transport-Security (HSTS) - Force HTTPS for 1 year
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Content-Security-Policy - Prevent XSS attacks
    # Adjusted policy to allow external resources needed by the frontend
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://static.cloudflareinsights.com https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https://api.sentinelflux.software https://api-sf01.sentinelflux.software wss://api.sentinelflux.software wss://api-sf01.sentinelflux.software https://cloudflareinsights.com https://cdn.jsdelivr.net; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # X-Frame-Options - Prevent clickjacking
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    
    # X-Content-Type-Options - Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Referrer-Policy - Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions-Policy - Control browser features
    response.headers["Permissions-Policy"] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "accelerometer=()"
    )
    
    return response

# Middleware to add rate limit headers
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    try:
        response = await call_next(request)
        if hasattr(request.state, "view_rate_limit"):
            limiter._inject_headers(response, request.state.view_rate_limit)
        return response
    except Exception as e:
        logger.error("Unhandled exception occurred:", exc_info=True)
        traceback_str = traceback.format_exc()
        logger.error(f"Traceback: {traceback_str}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An error occurred while processing the request.", "error": str(e), "traceback": traceback_str},
        )

# Include routers - MUST be after middleware
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(dnflux_router, prefix="/dnflux", tags=["dnflux"])
app.include_router(search_domain_router, prefix="/search", tags=["search"])
app.include_router(process_status_router, tags=["process_status"])
app.include_router(live_map_router, prefix="/visualize", tags=["visualize"])

# GraphQL endpoint
graphql_router = create_graphql_router()
app.include_router(graphql_router, tags=["GraphQL"])


# HTTPS redirect middleware for production
# TESTING = os.getenv("TESTING", "False").lower() in ("true", "1", "yes")

# if not TESTING:
#     @app.middleware("http")
#     async def redirect_to_https(request: Request, call_next):
#         if request.url.scheme != "https":
#             url = request.url.replace(scheme="https")
#             return RedirectResponse(url=str(url))
#         return await call_next(request)

# Root endpoint - now requires authentication
@app.get("/", include_in_schema=False)
async def root(request: Request, current_user = Security(get_current_user)):
    """Authenticated root endpoint. Rejects any requests with query parameters. Requires JWT token or API key."""
    if request.query_params:
        return JSONResponse(
            content={"detail": "Query parameters are not allowed on the root endpoint."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    return JSONResponse(content={
        "data": {"message": "SentinelFlux Project by IIUM KICT Student"},
        "remark": "2.0.0",
        "status": "running",
        "authenticated": True,
        "auth_method": current_user.get("auth_method", "unknown"),
        "client_id": current_user.get("client_id", "unknown")
    }, status_code=status.HTTP_200_OK)
