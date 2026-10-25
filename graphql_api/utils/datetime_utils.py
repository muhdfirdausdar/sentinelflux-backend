"""
Datetime and Timezone Utility Functions
Handles timezone conversions for GraphQL queries
Database timezone: UTC+8 (Asia/Singapore, Asia/Kuala_Lumpur)
"""
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional
import pytz
from dateutil import parser

# Database timezone is UTC+8
DB_TIMEZONE = dt_timezone(timedelta(hours=8))
DB_TIMEZONE_NAME = "UTC+08:00"


def parse_datetime_with_timezone(datetime_str: str) -> tuple[datetime, str]:
    """
    Parse datetime string and extract timezone information.
    
    Args:
        datetime_str: Datetime string in any format (with or without timezone)
    
    Returns:
        Tuple of (datetime in UTC+8, original timezone name in standard format)
    
    Examples:
        "2025-10-17T06:58:25.556411+00:00" -> (datetime in UTC+8, "UTC+00:00")
        "2025-10-17T06:58:25+08:00" -> (datetime in UTC+8, "UTC+08:00")
        "2025-10-17T06:58:25+01:00" -> (datetime in UTC+8, "UTC+01:00")
        "2025-10-17 06:58:25" -> (datetime in UTC+8, "UTC+08:00")
    """
    try:
        # Parse the datetime string (handles multiple formats)
        dt = parser.parse(datetime_str)
        
        # Extract timezone info
        if dt.tzinfo is None:
            # No timezone info, assume UTC+8 (database timezone)
            dt = dt.replace(tzinfo=DB_TIMEZONE)
            original_tz = DB_TIMEZONE_NAME
        else:
            # Format the original timezone as "UTC±HH:MM"
            offset = dt.utcoffset()
            if offset is not None:
                total_seconds = int(offset.total_seconds())
                hours = total_seconds // 3600
                minutes = (abs(total_seconds) % 3600) // 60
                
                # Format as UTC+HH:MM or UTC-HH:MM
                sign = '+' if hours >= 0 else '-'
                original_tz = f"UTC{sign}{abs(hours):02d}:{minutes:02d}"
            else:
                original_tz = "UTC+00:00"
            
            # Convert to UTC+8 for database operations
            dt = dt.astimezone(DB_TIMEZONE)
        
        return dt, original_tz
    except Exception as e:
        raise ValueError(f"Invalid datetime format: {datetime_str}. Error: {str(e)}")


def normalize_to_utc8(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Normalize datetime string to UTC+8 timezone-aware datetime.
    This is used for database queries.
    
    Args:
        datetime_str: Datetime string in any format
    
    Returns:
        Timezone-aware datetime in UTC+8, or None if input is None
    
    Examples:
        "2025-10-17T06:58:25.556411+00:00" -> datetime(2025, 10, 17, 14, 58, 25, tzinfo=UTC+8)
        "2025-10-17T14:58:25+08:00" -> datetime(2025, 10, 17, 14, 58, 25, tzinfo=UTC+8)
    """
    if datetime_str is None:
        return None
    
    dt, _ = parse_datetime_with_timezone(datetime_str)
    return dt


def normalize_to_utc(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Alias for normalize_to_utc8 for backward compatibility.
    Actually returns UTC+8 datetime.
    """
    return normalize_to_utc8(datetime_str)


def convert_datetime_to_timezone(dt: datetime, target_timezone: str) -> datetime:
    """
    Convert UTC+8 datetime to target timezone.
    
    Args:
        dt: Datetime in UTC+8 (database timezone)
        target_timezone: Target timezone name (e.g., "UTC", "Asia/Singapore", "UTC+08:00")
    
    Returns:
        Datetime converted to target timezone
    """
    if dt is None:
        return None
    
    # Ensure datetime is timezone-aware in UTC+8
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DB_TIMEZONE)
    elif dt.tzinfo != DB_TIMEZONE:
        dt = dt.astimezone(DB_TIMEZONE)
    
    # If target is same as database timezone, return as-is
    if target_timezone == DB_TIMEZONE_NAME or target_timezone == "UTC+08:00":
        return dt
    
    # Handle offset-based timezones like "UTC+08:00", "UTC", etc.
    try:
        if target_timezone.startswith("UTC"):
            if target_timezone == "UTC":
                # Convert to UTC (UTC+0)
                offset = timedelta(hours=0)
            elif "+" in target_timezone or "-" in target_timezone:
                # Parse offset like "UTC+08:00" or "UTC-05:00"
                offset_str = target_timezone[3:]  # Remove "UTC"
                sign = 1 if offset_str[0] == '+' else -1
                offset_str = offset_str[1:]  # Remove sign
                hours = int(offset_str.split(":")[0])
                minutes = int(offset_str.split(":")[1]) if ":" in offset_str else 0
                
                # Create timezone with offset
                offset = timedelta(hours=sign * hours, minutes=sign * minutes)
            else:
                offset = timedelta(hours=0)
            
            tz = dt_timezone(offset)
            return dt.astimezone(tz)
        else:
            # Use pytz for named timezones like "Asia/Singapore"
            tz = pytz.timezone(target_timezone)
            return dt.astimezone(tz)
    except:
        # Fallback to UTC+8 if timezone is invalid
        return dt


def get_current_utc() -> datetime:
    """
    Get current datetime in UTC+8 (database timezone).
    
    Returns:
        Current datetime in UTC+8 timezone
    """
    return datetime.now(DB_TIMEZONE)


def get_current_utc8() -> datetime:
    """
    Get current datetime in UTC+8.
    Alias for get_current_utc().
    
    Returns:
        Current datetime in UTC+8 timezone
    """
    return get_current_utc()
