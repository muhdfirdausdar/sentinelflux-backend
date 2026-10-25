"""
Process Status Routes
API endpoints to check the status of background processes
"""

from fastapi import APIRouter, HTTPException, Depends, Security
from typing import Dict, Any
from utils.async_log import get_logger
from utils.auth import get_current_user
from process_switch import get_process_status, log_process_configuration

logger = get_logger("process_status_routes")

router = APIRouter()

@router.get("/process/status")
async def get_all_process_status(current_user = Security(get_current_user)) -> Dict[str, Any]:
    """
    Get the status of all background processes
    
    Returns:
        Process status information
    """
    try:
        status = get_process_status()
        
        enabled_count = sum(status.values())
        total_count = len(status)
        
        return {
            "status": "success",
            "processes": status,
            "summary": {
                "enabled": enabled_count,
                "total": total_count,
                "all_enabled": enabled_count == total_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting process status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/process/log-config")
async def log_current_configuration(current_user = Security(get_current_user)) -> Dict[str, Any]:
    """
    Log the current process configuration to the logs
    
    Returns:
        Success message
    """
    try:
        log_process_configuration()
        
        return {
            "status": "success",
            "message": "Process configuration logged to server logs"
        }
        
    except Exception as e:
        logger.error(f"Error logging process configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
