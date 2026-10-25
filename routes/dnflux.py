"""
DNFlux API Routes
Routes for communicating with DNFlux VM2 service
"""

import os
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, Response, status, Security
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from utils.async_log import get_logger
from dnflux_pool import dnflux_pool
from tasks.dnflux_metrics_fetcher import get_latest_metrics_from_buffer
from schemas.return_response import ResponseStatus, ReturnResponse
from tasks.dns_data_formatter import format_dns_data
# Import the hybrid authentication dependency
from utils.auth import get_current_user
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = get_logger("dnflux_routes")

# Environment variable to control SSE behavior
# Set DNFLUX_SSE_ALWAYS_SEND=true to always send data even if unchanged
DNFLUX_SSE_ALWAYS_SEND = os.getenv('DNFLUX_SSE_ALWAYS_SEND', 'false').lower() in ('true', '1', 'yes')

# Environment variable to control SSE interval (in seconds)
DNFLUX_SSE_INTERVAL = int(os.getenv('DNFLUX_SSE_INTERVAL', '5'))

router = APIRouter()

@router.get("/metrics")
async def stream_dnflux_metrics(
    current_user = Security(get_current_user)
):
    """
    Stream DNFlux metrics from Redis buffer using Server-Sent Events (SSE)
    
    This endpoint provides real-time streaming of DNFlux metrics that are 
    fetched every 30 seconds by the background task and buffered in Redis.
    
    Environment Variables:
        DNFLUX_SSE_ALWAYS_SEND: Set to 'true' to always send data every interval,
                                even if metrics haven't changed. Default: 'false'
                                (only sends when data changes, heartbeat otherwise)
        DNFLUX_SSE_INTERVAL: SSE stream interval in seconds. Default: '5'
    
    All events (data, heartbeat, error, no_data) are wrapped in:
        {"status": "good"|"normal"|"error", "remark": "...", "data": { ...metrics... }}
    """
    logger.info("🚀 Starting DNFlux metrics SSE stream...")
    async def event_generator():
        event_count = 0
        last_data_hash = None
        logger.info(f"🎛️ SSE Always Send Mode: {'ON' if DNFLUX_SSE_ALWAYS_SEND else 'OFF'}")
        logger.info(f"⏱️ SSE Interval: {DNFLUX_SSE_INTERVAL} seconds")
        if DNFLUX_SSE_ALWAYS_SEND:
            logger.info("📡 Will send data every interval regardless of changes")
        else:
            logger.info("📡 Will only send data when metrics change (heartbeat when unchanged)")
        while True:
            event_count += 1
            try:
                buffer_data = await get_latest_metrics_from_buffer()
                if buffer_data:
                    metrics_data = buffer_data.copy()
                    buffer_timestamp = metrics_data.pop("buffer_timestamp", None)
                    source = metrics_data.pop("source", None)
                    # Exclude volatile timestamp fields from hash comparison so
                    # that only meaningful metric changes trigger a new event.
                    # Keep the ts and fetch_timestamp fields in the payload we send,
                    # but don't include them when computing the hash.
                    hash_exclude_keys = {"ts", "fetch_timestamp"}
                    metrics_for_hash = {k: v for k, v in metrics_data.items() if k not in hash_exclude_keys}
                    current_data_hash = hash(json.dumps(metrics_for_hash, sort_keys=True))
                    should_send_data = (
                        DNFLUX_SSE_ALWAYS_SEND or
                        current_data_hash != last_data_hash or
                        event_count == 1
                    )
                    if should_send_data:
                        envelope = {
                            "status": "good",
                            "remark": "New data" if event_count == 1 or current_data_hash != last_data_hash else "Periodic update",
                            "data": metrics_data
                        }
                        yield f"event: message\ndata: {json.dumps(envelope)}\n\n"
                        last_data_hash = current_data_hash
                        logger.debug(f"📡 Sent DNFlux metrics SSE event #{event_count}")
                        logger.debug(f"📊 Metrics timestamp: {metrics_data.get('ts', 'unknown')}")
                    else:
                        heartbeat = {
                            "status": "normal",
                            "remark": "No Change",
                            "data": {
                                "last_update": buffer_timestamp
                            }
                        }
                        yield f"event: heartbeat\ndata: {json.dumps(heartbeat)}\n\n"
                        logger.debug(f"💓 Sent heartbeat SSE event #{event_count}")
                else:
                    no_data = {
                        "status": "error",
                        "remark": "No Data",
                        "data": {}
                    }
                    yield f"event: no_data\ndata: {json.dumps(no_data)}\n\n"
                    logger.debug(f"📭 Sent no-data SSE event #{event_count}")
            except Exception as e:
                logger.error(f"❌ Error in DNFlux metrics SSE stream event #{event_count}: {e}")
                error_data = {
                    "status": "error",
                    "remark": str(e),
                    "data": {
                        "event_count": event_count
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
            await asyncio.sleep(DNFLUX_SSE_INTERVAL)
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )



@router.get("/metrics/json")
async def get_dnflux_metrics_json(current_user = Security(get_current_user)):
    """
    Get the latest DNFlux metrics as JSON (non-streaming)
    
    Returns:
        {
            "status": "good"|"error",
            "remark": "...",
            "data": { ...metrics... }
        }
    """
    try:
        buffer_data = await get_latest_metrics_from_buffer()
        if buffer_data:
            metrics_data = buffer_data.copy()
            buffer_timestamp = metrics_data.pop("buffer_timestamp", None)
            source = metrics_data.pop("source", None)
            envelope = {
                "status": "good",
                "remark": "Latest metrics",
                "data": metrics_data
            }
            return envelope
        else:
            return {
                "status": "error",
                "remark": "No DNFlux metrics available in Redis buffer",
                "data": {}
            }
    except Exception as e:
        logger.error(f"❌ Error fetching DNFlux metrics JSON: {e}")
        return {
            "status": "error",
            "remark": f"Error retrieving metrics: {str(e)}",
            "data": {}
        }


# Task creation request model for user-initiated scheduled tasks
class UserTaskCreateRequest(BaseModel):
    """Request model for user-initiated scheduled DNS monitoring tasks"""
    domain: str  # Single domain name (required)
    total_duration: int  # Total monitoring duration in minutes (required)
    minute_dig_every: int  # Interval between DNS queries in minutes (required)
    email: str = None  # Optional user email for notifications


# Task creation request model
class TaskCreateRequest(BaseModel):
    """Request model for creating a task on DNFlux VM"""
    domain: str = None  # Single domain name
    file_path: str = None  # Or file path for bulk tasks
    ops: str = None  # DNS operations (comma-separated: A, AAAA, NS, MX, TXT, CNAME, SOA, PTR, ALL)
    special_ops: str = None  # Optional special operations (comma-separated: whois, geo)
    mode: str = "immediate"  # "immediate" or "schedule"
    priority: int = 40  # Task priority (0-255, default: 40)
    resolver: str = None  # Optional DNS resolver (e.g., "8.8.8.8")
    remark: str = None  # Optional remark
    is_unrated: bool = False  # Flag for unrated domains
    addon: Dict[str, Any] = None  # Optional additional data
    datetime_str: str = None  # Required for schedule mode (various formats supported)
    minute_offset: int = None  # Alternative for schedule mode (minutes from now)


@router.post("/task-create", response_model=ReturnResponse)
async def create_user_scheduled_task(
    task_data: UserTaskCreateRequest,
    current_user = Security(get_current_user)
):
    """
    Create a scheduled DNS monitoring task for user requests
    
    This endpoint is designed for user-initiated scheduled DNS monitoring tasks.
    It constructs the appropriate payload and forwards it to the DNFlux VM.
    
    Request Body:
        - domain: Domain name to monitor (required)
        - total_duration: Total monitoring duration in minutes (required)
        - minute_dig_every: Interval between DNS queries in minutes (required)
        - email: Optional user email for notifications
    
    Returns:
        ReturnResponse with status, remark, and data from DNFlux
    
    Example Request:
        {
            "domain": "example.com",
            "total_duration": 15,
            "minute_dig_every": 2,
            "email": "user@example.com"
        }
    
    Example Response (Success):
        {
            "status": "good",
            "remark": "Successfully created 1 tasks",
            "data": {
                "success": true,
                "task_ids": ["019a44cb-e67d-7ad7-a863-12425ab82602"],
                "domains_count": 1,
                "domains": ["example.com"],
                "mode": "schedule",
                "priority": 10,
                "user_request_info": {
                    "total_expected_run": 12,
                    "total_duration": 120,
                    "minute_dig_every": 10
                }
            }
        }
    
    Example Response (Error):
        {
            "status": "error",
            "remark": "minute_dig_every (120) cannot be greater than total_duration (60)",
            "data": {
                "success": false,
                "error": "minute_dig_every (120) cannot be greater than total_duration (60)",
                "validation_errors": []
            }
        }
    """
    try:
        logger.info(f"📝 Creating user scheduled task for domain: {task_data.domain}")
        
        # Get current time in the required format
        from datetime import datetime
        import pytz
        
        # Use Asia/Kuala_Lumpur timezone (UTC+8)
        tz = pytz.timezone('Asia/Kuala_Lumpur')
        current_time = datetime.now(tz)
        datetime_str = current_time.strftime("%Y-%m-%d %H:%M:%S%z")
        # Format timezone offset correctly (e.g., +08 instead of +0800)
        datetime_str = datetime_str[:-2] + datetime_str[-2:]
        
        # Construct the payload for DNFlux
        payload = {
            "domain": task_data.domain,
            "special_ops": "routine",
            "mode": "schedule",
            "datetime_str": datetime_str,
            "addon": {
                "is_user_request": True,
                "total_duration": task_data.total_duration,
                "minute_dig_every": task_data.minute_dig_every
            }
        }
        
        # Add email if provided
        if task_data.email:
            payload["addon"]["email"] = task_data.email
        
        logger.info(f"📤 Sending payload to DNFlux: {payload}")
        
        # Make POST request to DNFlux VM
        response = await dnflux_pool.request_with_retry(
            method="POST",
            endpoint="/task/create",
            json=payload,
            timeout=30.0
        )
        
        # Parse response
        if response.status_code == 200:
            result = response.json()
            
            # Extract status and remark from DNFlux response
            dnflux_status = result.get("status", "error")
            dnflux_remark = result.get("remark", "Unknown response")
            dnflux_data = result.get("data", {})
            # If user provided an email in the request, include it in the
            # response payload so the client receives the email back.
            try:
                if task_data.email:
                    if isinstance(dnflux_data, dict):
                        dnflux_data.setdefault('email', task_data.email)
            except Exception:
                # Don't fail the whole request if we can't attach the email
                logger.debug("Could not attach email to DNFlux response payload")
            
            # Map DNFlux status to our ResponseStatus
            if dnflux_status == "success":
                response_status = ResponseStatus.good
            else:
                response_status = ResponseStatus.error
            
            logger.info(f"✅ DNFlux response received - Status: {dnflux_status}")
            
            return ReturnResponse(
                status=response_status,
                remark=dnflux_remark,
                data=dnflux_data
            )
        else:
            # HTTP error
            logger.error(f"❌ DNFlux VM returned HTTP {response.status_code}")
            return ReturnResponse(
                status=ResponseStatus.error,
                remark=f"DNFlux VM error: HTTP {response.status_code}",
                data={"status_code": response.status_code, "response": response.text}
            )
            
    except Exception as e:
        logger.error(f"❌ Error creating user scheduled task: {e}")
        return ReturnResponse(
            status=ResponseStatus.error,
            remark=f"Internal error: {str(e)}",
            data={}
        )


@router.post("/task/create", response_model=ReturnResponse)
async def create_dnflux_task(
    task_data: TaskCreateRequest,
    current_user = Security(get_current_user)
):
    """
    Create a DNS analysis task on the DNFlux VM
    
    This endpoint forwards task creation requests to the DNFlux VM2 service.
    
    Request Body:
        - domain: Single domain name (or use file_path for bulk)
        - ops: DNS operations (comma-separated: A, AAAA, NS, MX, TXT, CNAME, SOA, PTR, ALL)
        - special_ops: Optional special operations (comma-separated: whois, geo)
        - mode: "immediate" or "schedule" (default: "immediate")
        - priority: Task priority 0-255 (default: 40)
        - resolver: Optional DNS resolver (e.g., "8.8.8.8")
        - remark: Optional task description
        - is_unrated: Flag for unrated domains (default: False)
        - addon: Optional additional data as dict
        - datetime_str: Required for schedule mode (formats: "YYYY-MM-DD HH:MM:SS+00", etc.)
        - minute_offset: Alternative for schedule mode (minutes from now)
    
    Returns:
        ReturnResponse with status, remark, and data
    
    Example Request:
        {
            "domain": "example.com",
            "ops": "A,AAAA,MX",
            "special_ops": "whois,geo",
            "mode": "immediate",
            "priority": 40,
            "remark": "Test DNS analysis"
        }
    
    Example Response (Success):
        {
            "status": "good",
            "remark": "Task created successfully",
            "data": {
                "task_id": "12345",
                "domain": "example.com",
                "status": "queued"
            }
        }
    
    Example Response (Error):
        {
            "status": "error",
            "remark": "Task creation failed: Invalid domain format",
            "data": {}
        }
    """
    try:
        logger.info(f"📝 Creating DNFlux task for domain: {task_data.domain or task_data.file_path}")
        
        # Prepare request payload
        payload = task_data.dict(exclude_none=True)
        
        # Make POST request to DNFlux VM
        response = await dnflux_pool.request_with_retry(
            method="POST",
            endpoint="/task/create",
            json=payload,
            timeout=30.0
        )
        
        # Parse response
        if response.status_code == 200:
            result = response.json()
            
            # Check if task creation was successful
            if result.get("success", False):
                logger.info(f"✅ DNFlux task created successfully")
                return ReturnResponse(
                    status=ResponseStatus.good,
                    remark="Task created successfully",
                    data=result
                )
            else:
                # Task creation failed
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ DNFlux task creation failed: {error_msg}")
                return ReturnResponse(
                    status=ResponseStatus.error,
                    remark=f"Task creation failed: {error_msg}",
                    data=result
                )
        else:
            # HTTP error
            logger.error(f"❌ DNFlux VM returned HTTP {response.status_code}")
            return ReturnResponse(
                status=ResponseStatus.error,
                remark=f"DNFlux VM error: HTTP {response.status_code}",
                data={"status_code": response.status_code, "response": response.text}
            )
            
    except Exception as e:
        logger.error(f"❌ Error creating DNFlux task: {e}")
        return ReturnResponse(
            status=ResponseStatus.error,
            remark=f"Internal error: {str(e)}",
            data={}
        )


@router.get("/user-task", response_model=ReturnResponse)
async def get_user_task_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Security(get_current_user)
):
    """
    Get user task results by task ID
    
    This endpoint checks task completion status from DNFlux VM and retrieves
    formatted DNS data from the database if the task is completed.
    
    Query Parameters:
        - task_id: UUID of the task to retrieve
    
    Returns:
        ReturnResponse with status, remark, and data including formatted results
    
    Example Request:
        GET /user-task?task_id=019a44cb-e67d-7ad7-a863-12425ab82602
    
    Example Response (Completed):
        {
            "status": "good",
            "remark": "Task completed",
            "data": {
                "task_id": "019a70c2-d14b-71b7-92d5-c8655df90e62",
                "found_in_history": true,
                "remark": "user done",
                "task_metadata": {
                    "domain_name": "x.com",
                    "start_time": "2025-11-11T02:33:30.534463+00:00",
                    "end_time": "2025-11-11T02:36:25.721341+00:00",
                    "execution_duration": "00:02:55"
                },
                "result_data": "formatted DNS data here..."
            }
        }
    
    Example Response (In Progress):
        {
            "status": "normal",
            "remark": "Task currently being processed",
            "data": {
                "task_id": "019a44cb-e67d-7ad7-a863-12425ab82602",
                "found_in_history": true,
                "remark": "5/12",
                "task_metadata": {...}
            }
        }
    
    Example Response (Not Found):
        {
            "status": "error",
            "remark": "Task not found or yet to be processed",
            "data": {
                "task_id": "019a44cb-e67d-7ad7-a863-12425ab82602",
                "found_in_history": false
            }
        }
    """
    try:
        logger.info(f"📋 Fetching user task results for task_id: {task_id}")
        
        # Step 1: Check task completion status from DNFlux VM
        response = await dnflux_pool.request_with_retry(
            method="GET",
            endpoint=f"/task/task-complete?task_id={task_id}",
            timeout=30.0
        )
        
        # Parse response
        if response.status_code != 200:
            logger.error(f"❌ DNFlux VM returned HTTP {response.status_code}")
            return ReturnResponse(
                status=ResponseStatus.error,
                remark=f"DNFlux VM error: HTTP {response.status_code}",
                data={"status_code": response.status_code, "response": response.text}
            )
        
        result = response.json()
        dnflux_status = result.get("status", "unknown")
        dnflux_message = result.get("message", "")
        dnflux_data = result.get("data", {})
        
        logger.info(f"📊 DNFlux task status: {dnflux_status}")
        
        # Step 2: Handle different task statuses
        if dnflux_status == "not_found":
            # Task not found or not yet processed
            return ReturnResponse(
                status=ResponseStatus.error,
                remark=dnflux_message or "Task not found or yet to be processed",
                data=dnflux_data
            )
        
        elif dnflux_status == "in_progress":
            # Task is still in progress
            return ReturnResponse(
                status=ResponseStatus.normal,
                remark=dnflux_message or "Task currently being processed",
                data=dnflux_data
            )
        
        elif dnflux_status == "completed":
            # Task is completed - fetch and format DNS data
            logger.info(f"✅ Task completed - fetching DNS data from database")
            
            # Step 3: Fetch raw data from database
            query = text("""
                SELECT run_number, raw_data, end_time
                FROM user_request_data
                WHERE task_id = :task_id
                ORDER BY run_number ASC
            """)
            
            db_result = await db.execute(query, {"task_id": task_id})
            rows = db_result.fetchall()
            
            if not rows:
                logger.warning(f"⚠️ No DNS data found in database for task_id: {task_id}")
                return ReturnResponse(
                    status=ResponseStatus.error,
                    remark="Task completed but no DNS data found in database",
                    data=dnflux_data
                )
            
            logger.info(f"📦 Found {len(rows)} DNS records for task_id: {task_id}")
            
            # Step 4: Format each raw data entry and concatenate
            formatted_results = []
            for row in rows:
                run_number = row[0]
                raw_data = row[1]  # JSONB data
                end_time = row[2]
                
                try:
                    # Format the raw DNS data
                    formatted = format_dns_data(raw_data)
                    formatted_output = formatted.get("formatted_output", "")
                    
                    # Add separator with run information
                    separator = f"\\n\\n{'='*80}\\n"
                    separator += f"Run #{run_number} - Completed at: {end_time}\\n"
                    separator += f"{'='*80}\\n\\n"
                    
                    formatted_results.append(separator + formatted_output)
                    
                    logger.debug(f"✅ Formatted run #{run_number}")
                
                except Exception as format_error:
                    logger.error(f"❌ Error formatting run #{run_number}: {format_error}")
                    formatted_results.append(f"\\n\\nRun #{run_number}: Error formatting data - {str(format_error)}\\n\\n")
            
            # Concatenate all formatted results
            concatenated_result = "\\n".join(formatted_results)
            
            # Step 5: Prepare final response data
            response_data = dnflux_data.copy()
            response_data["result_data"] = concatenated_result
            response_data["total_runs"] = len(rows)
            
            logger.info(f"✅ Successfully formatted {len(rows)} DNS records")
            
            return ReturnResponse(
                status=ResponseStatus.good,
                remark=dnflux_message or "Task completed",
                data=response_data
            )
        
        else:
            # Unknown status
            logger.warning(f"⚠️ Unknown task status: {dnflux_status}")
            return ReturnResponse(
                status=ResponseStatus.error,
                remark=f"Unknown task status: {dnflux_status}",
                data=dnflux_data
            )
    
    except Exception as e:
        logger.error(f"❌ Error fetching user task results: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return ReturnResponse(
            status=ResponseStatus.error,
            remark=f"Internal error: {str(e)}",
            data={}
        )

