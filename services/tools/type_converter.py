"""
Type conversion utilities for cursor pagination values.
Handles automatic conversion of string values to appropriate Python types
based on pattern recognition.
"""

import re
from datetime import datetime
from typing import Any, Tuple
from utils.async_log import get_logger

logger = get_logger("services.tools.type_converter")

# Regex patterns for different data types
DATETIME_PATTERNS = [
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$',  # ISO format with timezone
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$',  # ISO format without timezone
    r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$',  # Standard datetime format
]

INTEGER_PATTERN = r'^-?\d+$'
FLOAT_PATTERN = r'^-?\d+\.\d+$'


def detect_and_convert_type(value: Any) -> Tuple[Any, str]:
    """
    Automatically detect and convert string values to appropriate Python types.
    
    Args:
        value: The value to convert (can be any type)
    
    Returns:
        Tuple of (converted_value, detected_type)
        detected_type can be: 'datetime', 'int', 'float', 'string', 'unchanged'
    """
    # If not a string, return as-is
    if not isinstance(value, str):
        return value, 'unchanged'
    
    # Try datetime patterns first
    for pattern in DATETIME_PATTERNS:
        if re.match(pattern, value):
            try:
                # Handle ISO format with Z suffix
                datetime_str = value
                if value.endswith('Z'):
                    datetime_str = value[:-1] + '+00:00'
                
                converted = datetime.fromisoformat(datetime_str)
                return converted, 'datetime'
            except ValueError:
                continue
    
    # Try integer pattern
    if re.match(INTEGER_PATTERN, value):
        try:
            converted = int(value)
            return converted, 'int'
        except ValueError:
            pass
    
    # Try float pattern
    if re.match(FLOAT_PATTERN, value):
        try:
            converted = float(value)
            return converted, 'float'
        except ValueError:
            pass
    
    # Default to string
    return value, 'string'


def convert_cursor_values(sort_cursor_value: Any, after_id: Any) -> Tuple[Any, Any]:
    """
    Convert cursor pagination values to appropriate types.
    
    Args:
        sort_cursor_value: The cursor value for the sort column
        after_id: The ID value for stable pagination
    
    Returns:
        Tuple of (converted_sort_cursor_value, converted_after_id)
        
    Raises:
        ValueError: If conversion fails for critical values
    """
    try:
        # Convert sort cursor value
        converted_cursor_value = sort_cursor_value
        cursor_type = 'unchanged'
        
        if sort_cursor_value is not None:
            converted_cursor_value, cursor_type = detect_and_convert_type(sort_cursor_value)
            logger.debug(f"Converted sort_cursor_value: {sort_cursor_value} -> {converted_cursor_value} (type: {cursor_type})")
        
        # Convert after_id (should always be integer or None)
        converted_after_id = after_id
        if after_id is not None:
            if isinstance(after_id, str):
                if re.match(INTEGER_PATTERN, after_id):
                    converted_after_id = int(after_id)
                    logger.debug(f"Converted after_id: {after_id} -> {converted_after_id}")
                else:
                    raise ValueError(f"Invalid integer format for after_id: {after_id}")
        
        return converted_cursor_value, converted_after_id
        
    except Exception as e:
        logger.error(f"Error converting cursor values: {str(e)}")
        raise ValueError(f"Cursor value conversion failed: {str(e)}")


def safe_convert_cursor_values(sort_cursor_value: Any, after_id: Any) -> Tuple[Any, Any, bool]:
    """
    Safely convert cursor pagination values with error handling.
    
    Args:
        sort_cursor_value: The cursor value for the sort column
        after_id: The ID value for stable pagination
    
    Returns:
        Tuple of (converted_sort_cursor_value, converted_after_id, success)
        success is False if conversion failed
    """
    try:
        converted_cursor, converted_id = convert_cursor_values(sort_cursor_value, after_id)
        return converted_cursor, converted_id, True
    except Exception as e:
        logger.warning(f"Cursor value conversion failed, using original values: {str(e)}")
        return sort_cursor_value, after_id, False
