import os
import json
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response, status, Security
from fastapi.responses import StreamingResponse, PlainTextResponse
from utils.async_log import get_logger
from dnflux_pool import dnflux_pool
from tasks.dnflux_metrics_fetcher import get_latest_metrics_from_buffer
from tasks.top_stats import TopStatsFetcher

# Import session and data fetcher modules
from tasks.client_session import (
    get_session_info,
    update_session_info,
    refresh_session_expiry,
    delete_session
)
from tasks.live_map_fetcher import fetch_latest_live_map_data

# Import the hybrid authentication dependency
from utils.auth import get_current_user


VISUALIZE_SSE_INTERVAL = int(os.getenv('VISUALIZE_SSE_INTERVAL', '30'))

logger = get_logger("visualize_routes")

router = APIRouter()

@router.get("/top-stats")
async def get_top_stats(
    current_user = Security(get_current_user)
):
    """
    Get top 10 statistics for fast flux domains.
    
    Returns:
        JSON response with top 10 GeoIP countries, IPs, and nameservers
        
    Response format:
        {
            "status": "good"|"normal"|"error",
            "remark": "...",
            "data": {
                "last_update": "2025-10-26T12:34:56.789012",
                "top10_geoip": {"1": "USA", "2": "Malaysia", ...},
                "top10_ips": {"1": "192.168.1.1", ...},
                "top10_nameserver": {"1": "ns1.example.com", ...}
            }
        }
    """
    try:
        # Extract client_id from the decoded JWT payload (for logging)
        client_id = current_user.get("client_id")
        
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client ID not found in JWT token"
            )
        
        logger.info(f"Top stats requested by client: {client_id}")
        
        # Get top stats from cache
        fetcher = TopStatsFetcher()
        stats_result = await fetcher.get_top_stats()
        
        if stats_result is None:
            # No data available in cache
            logger.warning(f"No top stats data available for {client_id}")
            return {
                "status": "normal",
                "remark": "No top stats data available yet. Please try again later.",
                "data": {}
            }
        
        # Data available - return with last_update
        logger.info(f"Top stats sent to {client_id}, last updated: {stats_result.get('last_update')}")
        return {
            "status": "good",
            "remark": "Top stats retrieved successfully",
            "data": {
                "last_update": stats_result.get("last_update"),
                **stats_result.get("data", {})
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching top stats: {e}")
        import traceback
        logger.error(f"Top stats error traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "remark": f"Failed to retrieve top stats: {str(e)}",
            "data": {}
        }

@router.get("/live-map")

async def get_live_map(
    request: Request,
    authorization: Optional[str] = Header(None),
    current_user = Security(get_current_user)
):
    """
    Serve the live map HTML page for visualizing real-time data.

    All events (data, heartbeat, error, no_data) are wrapped in:
        {"status": "good"|"normal"|"error", "remark": "...", "data": { ...visualize_data... }}
    """
    # try:
    #     with open("static/live_map.html", "r") as file:
    #         html_content = file.read()
    #     return Response(content=html_content, media_type="text/html")
    # except FileNotFoundError:
    #     logger.error("Live map HTML file not found.")
    #     raise HTTPException(status_code=500, detail="Live map page not available.")

    # Extract client_id from the decoded JWT payload
    client_id = current_user.get("client_id")
    
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client ID not found in JWT token"
        )
    
    # Log connection establishment
    logger.info(f"SSE connection established for client: {client_id}")
    


    # def new_messages():
    #     # Check if data in table # STILL IN TEMPLATE
    #     # results = engine.execute('SELECT count(*) FROM sensors_view_1s')
    #     # if results.fetchone()[0] == 0:
    #     #     return None
    #     # else:
    #     #     return True
    #     pass

    async def event_generator():
        """
        SSE event generator for live map data streaming.
        
        Flow:
        1. Initial connection: Fetch all data (no session) or resume from last position
        2. Loop: Check for new data, send updates or heartbeat
        3. Disconnect: Clean up session
        """
        is_initial_load = True
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"SSE client disconnected: {client_id}")
                    # Clean up session on disconnect
                    await delete_session(client_id)
                    break

                # ===== STARTING SCENARIO: Initial connection =====
                if is_initial_load:
                    # Fetch all data for initial load (no session check)
                    logger.info(f"Initial load for client: {client_id}")
                    combined_data, latest_update, latest_domain_id = await fetch_latest_live_map_data(
                        last_update=None,
                        domain_id=None
                    )
                    
                    # Send initial data if available
                    if combined_data and latest_update and latest_domain_id:
                        # Update session with latest info
                        await update_session_info(client_id, latest_domain_id, latest_update)
                        
                        # Send data to client
                        init_message = {
                            "status": "good",
                            "remark": "Initial data loaded",
                            "data": combined_data
                        }
                        yield f"data: {json.dumps(init_message)}\n\n"
                        logger.info(f"Sent initial data to {client_id}: {len(combined_data)} IPs")
                    else:
                        # No data available
                        no_data_msg = {
                            "status": "normal",
                            "remark": "No data available",
                            "data": {}
                        }
                        yield f"data: {json.dumps(no_data_msg)}\n\n"
                        logger.info(f"No initial data available for {client_id}")
                    
                    # Mark initial load complete
                    is_initial_load = False
                    await asyncio.sleep(VISUALIZE_SSE_INTERVAL)
                    continue

                # ===== NEXT SCENARIO: Connected session - check for new data =====
                # Get current session info
                last_domain_id, last_update = await get_session_info(client_id)
                
                if last_domain_id is None or last_update is None:
                    # Session expired or lost - restart initial load
                    logger.warning(f"Session lost for {client_id}, restarting initial load")
                    is_initial_load = True
                    continue
                
                # Fetch new data since last update
                last_update_dt = datetime.fromisoformat(last_update)
                combined_data, latest_update, latest_domain_id = await fetch_latest_live_map_data(
                    last_update=last_update_dt,
                    domain_id=last_domain_id
                )
                
                # Check if there's new data
                if combined_data and latest_update and latest_domain_id:
                    # New data available - update session and send to client
                    await update_session_info(client_id, latest_domain_id, latest_update)
                    
                    update_message = {
                        "status": "good",
                        "remark": "New data update",
                        "data": combined_data
                    }
                    yield f"data: {json.dumps(update_message)}\n\n"
                    logger.info(f"Sent update to {client_id}: {len(combined_data)} new IPs")
                else:
                    # No new data - send heartbeat and refresh session
                    await refresh_session_expiry(client_id)
                    
                    heartbeat_msg = {
                        "status": "normal",
                        "remark": "No new data",
                        "data": {}
                    }
                    yield f"data: {json.dumps(heartbeat_msg)}\n\n"
                    logger.debug(f"Heartbeat sent to {client_id}")
                
                # Sleep before next iteration
                await asyncio.sleep(VISUALIZE_SSE_INTERVAL)
                
        except Exception as e:
            logger.error(f"Error in SSE stream for {client_id}: {e}")
            # Clean up session on error
            await delete_session(client_id)
            error_msg = {
                "status": "error",
                "remark": str(e),
                "data": {}
            }
            yield f"data: {json.dumps(error_msg)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

