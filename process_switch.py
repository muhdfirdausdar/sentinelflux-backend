"""
Process Switch Manager for SentinelFlux
Allows enabling/disabling background processes via environment variables for easier debugging.
"""

import os
import asyncio
from utils.async_log import get_logger

logger = get_logger("process_switch")

def is_process_enabled(process_name: str, default: bool = True) -> bool:
    """
    Check if a process is enabled via environment variable.
    
    Args:
        process_name: Name of the process (e.g., 'dnflux_metrics_fetcher')
        default: Default value if environment variable is not set
    
    Returns:
        True if process should be enabled, False otherwise
    
    Environment Variables:
        DISABLE_ALL_FEATURES=1|0
        ENABLE_DNFLUX_METRICS_FETCHER=1|0
        ENABLE_EMAILING_SERVICES=1|0
        (More processes can be added later)
    """
    # Check if all features are disabled first
    if os.getenv("DISABLE_ALL_FEATURES", "0").lower() in ("1", "true", "yes"):
        logger.warning(f"⚠️ {process_name} disabled via DISABLE_ALL_FEATURES=1")
        return False
    
    env_var = f"ENABLE_{process_name.upper()}"
    value = os.getenv(env_var, str(int(default)))
    enabled = value.lower() in ("1", "true", "yes", "on")
    
    if enabled:
        logger.info(f"✅ {process_name} enabled via {env_var}={value}")
    else:
        logger.warning(f"⚠️ {process_name} disabled via {env_var}={value}")
    
    return enabled

async def start_enabled_processes(app):
    """
    Start all enabled background processes based on environment configuration.
    
    Args:
        app: FastAPI application instance with initialized state
    """
    logger.info("🔄 Starting enabled background processes...")
    
    # Check first if all features are disabled
    if os.getenv("DISABLE_ALL_FEATURES", "0").lower() in ("1", "true", "yes"):
        logger.warning("⚠️ All features are disabled via DISABLE_ALL_FEATURES=1")
        app.state.background_tasks = []
        return

    # Initialize background tasks list
    app.state.background_tasks = []
    enabled_count = 0
    total_processes = 3  # DNFlux metrics fetcher + Top stats fetcher + Emailing services
    
    # 1. DNFlux Metrics Fetcher
    if is_process_enabled("dnflux_metrics_fetcher"):
        try:
            logger.info("🚀 Starting DNFlux metrics fetcher")
            from tasks import dnflux_metrics_loop
            
            dnflux_task = asyncio.create_task(dnflux_metrics_loop())
            app.state.background_tasks.append(dnflux_task)
            app.state.dnflux_metrics_task = dnflux_task
            
            enabled_count += 1
            logger.info("✅ DNFlux metrics fetcher started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start DNFlux metrics fetcher: {e}")
            import traceback
            logger.error(f"DNFlux metrics fetcher traceback: {traceback.format_exc()}")
            app.state.dnflux_metrics_task = None
    else:
        app.state.dnflux_metrics_task = None
    
    # 2. Top Stats Fetcher
    if is_process_enabled("top_stats_fetcher"):
        try:
            logger.info("🚀 Starting top stats fetcher")
            from tasks.top_stats import top_stats_loop
            
            top_stats_task = asyncio.create_task(top_stats_loop())
            app.state.background_tasks.append(top_stats_task)
            app.state.top_stats_task = top_stats_task
            
            enabled_count += 1
            logger.info("✅ Top stats fetcher started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start top stats fetcher: {e}")
            import traceback
            logger.error(f"Top stats fetcher traceback: {traceback.format_exc()}")
            app.state.top_stats_task = None
    else:
        app.state.top_stats_task = None
    
    # 3. Emailing Services
    if is_process_enabled("emailing_services"):
        try:
            logger.info("🚀 Starting emailing services loop")
            from emailing_services import emailing_services_loop

            emailing_task = asyncio.create_task(emailing_services_loop())
            app.state.background_tasks.append(emailing_task)
            app.state.emailing_task = emailing_task

            enabled_count += 1
            logger.info("✅ Emailing services started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start emailing services: {e}")
            import traceback
            logger.error(f"Emailing services traceback: {traceback.format_exc()}")
            app.state.emailing_task = None
    else:
        app.state.emailing_task = None
    
    # TODO: Add more processes here as they are developed
    # Example:
    # if is_process_enabled("another_process"):
    #     logger.info("Starting another process")
    #     another_task = asyncio.create_task(another_process_loop())
    #     app.state.background_tasks.append(another_task)
    #     enabled_count += 1
    
    logger.info(f"🎉 Process startup completed: {enabled_count}/{total_processes} processes enabled")

async def stop_enabled_processes(app):
    """
    Stop all running background processes gracefully.
    
    Args:
        app: FastAPI application instance
    """
    logger.info("🛑 Shutting down SentinelFlux - stopping background processes...")
    
    # Check first if all features are disabled
    if os.getenv("DISABLE_ALL_FEATURES", "0").lower() in ("1", "true", "yes"):
        logger.warning("⚠️ All features were disabled via DISABLE_ALL_FEATURES=1")
        return
    
    stopped_count = 0
    
    try:
        # Cancel all background tasks
        if hasattr(app.state, 'background_tasks') and app.state.background_tasks:
            logger.info(f"🛑 Cancelling {len(app.state.background_tasks)} background tasks...")
            
            for task in app.state.background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            stopped_count = len(app.state.background_tasks)
            logger.info("✅ All background tasks cancelled")
        
        # Wait a moment for tasks to clean up
        await asyncio.sleep(1)
        
        logger.info(f"✅ Background processes stopped: {stopped_count} processes")
        
    except Exception as e:
        logger.error(f"❌ Error during process shutdown: {str(e)}")
        import traceback
        logger.error(f"Shutdown traceback: {traceback.format_exc()}")
        raise

def get_process_status():
    """
    Get the current status of all process switches.
    
    Returns:
        dict: Process name -> enabled status
    """
    processes = [
        "dnflux_metrics_fetcher",
        "top_stats_fetcher",
        "emailing_services",
        # TODO: Add more processes here as they are developed
    ]
    
    # Check first if DISABLE_ALL_FEATURES is set
    if os.getenv("DISABLE_ALL_FEATURES", "0").lower() in ("1", "true", "yes"):
        return {process: False for process in processes}

    return {
        process: is_process_enabled(process)
        for process in processes
    }

def log_process_configuration():
    """Log the current process configuration for debugging."""
    logger.info("🔧 Current Process Configuration:")

    # Check if all features are disabled
    if os.getenv("DISABLE_ALL_FEATURES", "0").lower() in ("1", "true", "yes"):
        logger.warning("⚠️ All features are disabled via DISABLE_ALL_FEATURES=1")
        return

    status = get_process_status()
    
    for process_name, enabled in status.items():
        status_icon = "✅" if enabled else "❌"
        env_var = f"ENABLE_{process_name.upper()}"
        env_value = os.getenv(env_var, "1")  # Default to enabled
        logger.info(f"  {status_icon} {process_name}: {env_var}={env_value}")
    
    enabled_count = sum(status.values())
    total_count = len(status)
    logger.info(f"📊 Total: {enabled_count}/{total_count} processes enabled")
