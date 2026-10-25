import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Security, Request, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from utils.async_log import get_logger
from utils.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from services.pagination import get_paginated_response
from schemas.return_response import ResponseStatus, ReturnResponse
from schemas.pagination import  SortableColumns, FilterableColumns, FilterOperations, FieldTable
from database import get_db
from utils.input_sanitizer import InputSanitizer
from datetime import datetime
from enum import Enum
logger = get_logger("search_domain")


router = APIRouter()

"""
Expected URL format for pagination with cursor:
/domains?limit=5&?fields=domain_name,dom_last_seen,flux_type&sort=-last_seen&filters.status=active&filters.is_malicious=true&cursor=bGFzdF9zZWVuPTIwMjUtMDktMDJUMTU6MDA6MDBaJmlkPTEwOQ==

cursor is not available if it's the first page
the filter may have non or multiple filters
"""


# ============================================================================
# Pydantic Models for Request Validation
# ============================================================================

class SearchDomainParams(BaseModel):
    """
    Validated search parameters for domain search endpoint.
    Handles limit, cursor, sort, direction, and fields parameters.
    """
    limit: int = Field(default=10, ge=1, le=1000, description="Number of items per page")
    cursor: Optional[str] = Field(default=None, description="Base64 encoded cursor for pagination")
    sort: str = Field(default="-dom_last_seen", description="Sort parameter (prefix with - for descending)")
    direction: str = Field(default="next", description="Pagination direction: next or prev")
    fields: Optional[str] = Field(default=None, description="Comma-separated list of fields to return")
    
    # Internal validated fields (populated after validation)
    _sort_column: Optional[object] = None
    _is_descending: bool = False
    _field_objects: list = []
    _cursor_data: Optional[dict] = None
    
    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Validate direction parameter"""
        if v.lower() not in ["next", "prev"]:
            raise ValueError(f"Invalid direction: {v}. Allowed values: 'next', 'prev'")
        return v.lower()
    
    @field_validator('sort')
    @classmethod
    def validate_sort_format(cls, v: str) -> str:
        """Validate sort parameter format and column name"""
        # Parse sort parameter
        if v.startswith("-"):
            column = v[1:]
        else:
            column = v
        
        # Validate column exists
        column_obj = SortableColumns.find_column(column)
        if column_obj is None:
            raise ValueError(
                f"Invalid sort column: {column}. "
                f"Allowed columns: {SortableColumns.get_all_sortable()}"
            )
        
        return v
    
    @field_validator('cursor')
    @classmethod
    def validate_cursor_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate cursor is valid base64"""
        # Treat None or empty string as no cursor
        if v is None or v == "":
            return None
        
        try:
            # Try to decode to ensure it's valid base64
            raw = base64.urlsafe_b64decode(v.encode()).decode()
            # Try to parse as key=value pairs
            dict(item.split("=", 1) for item in raw.split("&"))
            return v
        except Exception:
            raise ValueError("Invalid cursor format. Must be a valid base64 encoded string.")
    
    @field_validator('fields')
    @classmethod
    def validate_fields_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate fields parameter format"""
        # Treat None or empty string as no fields specified (will return all fields)
        if v is None or v.strip() == "":
            return None
        
        # Parse comma-separated fields
        requested_fields = [field.strip() for field in v.split(",")]
        
        # Remove empty strings and duplicates
        requested_fields = list(set([field for field in requested_fields if field]))
        
        if not requested_fields:
            return None  # Treat as no fields specified
        
        # Validate fields using FieldTable class
        valid_field_enums, invalid_fields = FieldTable.validate_fields(requested_fields)
        
        if invalid_fields:
            available_fields = FieldTable.get_all_field_names()
            raise ValueError(
                f"Invalid field(s) found: {invalid_fields}. "
                f"Available fields are: {sorted(available_fields)}. "
                f"Please check the field names and ensure they match exactly (case-sensitive)."
            )
        
        if not valid_field_enums:
            raise ValueError("No valid fields found after validation. Please provide at least one valid field.")
        
        return v
    
    def parse_sort(self) -> tuple[object, bool]:
        """Parse sort parameter into column object and descending flag"""
        if self.sort.startswith("-"):
            column = self.sort[1:]
            is_desc = True
        else:
            column = self.sort
            is_desc = False
        
        column_obj = SortableColumns.find_column(column)
        return column_obj, is_desc
    
    def parse_cursor(self) -> Optional[dict]:
        """Parse cursor into dictionary"""
        if not self.cursor:
            return None
        
        try:
            raw = base64.urlsafe_b64decode(self.cursor.encode()).decode()
            return dict(item.split("=", 1) for item in raw.split("&"))
        except Exception:
            raise ValueError("Invalid cursor format")
    
    def parse_fields(self) -> list[object]:
        """Parse fields parameter into field column objects"""
        if not self.fields:
            return FieldTable.get_all_fields()
        
        # Parse comma-separated fields
        requested_fields = [field.strip() for field in self.fields.split(",")]
        requested_fields = list(set([field for field in requested_fields if field]))
        
        # Validate and get field enums
        valid_field_enums, _ = FieldTable.validate_fields(requested_fields)
        return valid_field_enums


class DynamicFilters(BaseModel):
    """
    Handles dynamic filter query parameters.
    Extracts and validates filters from request query parameters.
    Format: filters.column.operation=value
    """
    filter_cols: list = Field(default_factory=list)
    filter_ops: list = Field(default_factory=list)
    filter_values: list = Field(default_factory=list)
    
    @classmethod
    def from_request(cls, request: Request) -> "DynamicFilters":
        """
        Extract and validate filters from request query parameters.
        Returns DynamicFilters instance with validated filter data.
        """
        filter_cols = []
        filter_ops = []
        filter_values = []
        
        for key, value in request.query_params.items():
            if key.startswith("filters."):
                # Parse filter key: filters.column.operation
                parts = key.replace("filters.", "").split(".")
                
                if len(parts) == 2:
                    # filters.column.operation format
                    filter_key, operation = parts
                elif len(parts) == 1:
                    # Legacy format: filters.column (default to eq)
                    filter_key = parts[0]
                    operation = "eq"
                else:
                    raise ValueError(
                        f"Invalid filter format: {key}. Expected: filters.column.operation"
                    )
                
                # Validate filter column exists
                column_obj = FilterableColumns.find_column(filter_key)
                if column_obj is None:
                    raise ValueError(
                        f"Invalid filter column: {filter_key}. "
                        f"Allowed columns: {FilterableColumns.get_all_filterable()}"
                    )
                
                # Validate operation
                operation_obj = FilterOperations.find_operation(operation)
                if operation_obj is None:
                    raise ValueError(
                        f"Invalid filter operation: {operation}. "
                        f"Allowed operations: {FilterOperations.get_all_operations()}"
                    )
                
                # Add to arrays
                filter_cols.append(column_obj)
                filter_ops.append(operation_obj)
                filter_values.append(value)
        
        return cls(
            filter_cols=filter_cols,
            filter_ops=filter_ops,
            filter_values=filter_values
        )


# ============================================================================
# Helper Functions for Cursor and Sort Validation
# ============================================================================

def encode_cursor(data: dict) -> str:
    """Encode cursor dictionary to base64 string"""
    raw = "&".join(f"{k}={v}" for k, v in data.items())
    return base64.urlsafe_b64encode(raw.encode()).decode()

def decode_cursor(cursor: str) -> dict:
    """Decode base64 cursor string to dictionary"""
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    return dict(item.split("=", 1) for item in raw.split("&"))

def extract_cursor_sort_info(cursor_data: Optional[dict]) -> tuple[Optional[object], Optional[str]]:
    """
    Extract sort column object and value from cursor data.
    Returns: (sort_column_obj, sort_value)
    """
    if not cursor_data:
        return None, None
    
    # Check if cursor has required domain_id
    if "domain_id" not in cursor_data:
        error_info = "Cursor must contain 'domain_id' field"
        logger.error(error_info)
        raise ValueError(error_info)
    
    # Find the sort column (any field other than domain_id and next_item_pos)
    cursor_sort_fields = {k: v for k, v in cursor_data.items() if k not in ["domain_id", "next_item_pos"]}
    
    if len(cursor_sort_fields) == 0:
        error_info = "Cursor must contain a sort column field in addition to domain_id"
        logger.error(error_info)
        raise ValueError(error_info)
    
    if len(cursor_sort_fields) > 1:
        error_info = f"Cursor should contain exactly one sort field, found: {list(cursor_sort_fields.keys())}"
        logger.error(error_info)
        raise ValueError(error_info)
    
    # Get the sort field name and value
    cursor_sort_field_name = list(cursor_sort_fields.keys())[0]
    cursor_sort_field_value = cursor_sort_fields[cursor_sort_field_name]
    
    # Find the corresponding SortableColumn object
    cursor_sort_column_obj = SortableColumns.find_column(cursor_sort_field_name)
    if cursor_sort_column_obj is None:
        error_info = f"Cursor sort field '{cursor_sort_field_name}' is not a valid sortable column"
        logger.error(error_info)
        raise ValueError(error_info)
    
    logger.info(f"Cursor sort info extracted - Column: {cursor_sort_column_obj}, Value: {cursor_sort_field_value}")
    return cursor_sort_column_obj, cursor_sort_field_value

def validate_cursor_with_sort(cursor_sort_column_obj: Optional[object], url_sort_column_obj: object) -> None:
    """
    Validate that cursor sort column matches URL sort parameter.
    """
    if cursor_sort_column_obj is None:
        return  # No cursor means first page, nothing to validate
    
    # Check if the cursor sort column object matches the URL sort column object
    if cursor_sort_column_obj != url_sort_column_obj:
        cursor_col_name = getattr(cursor_sort_column_obj, 'value', str(cursor_sort_column_obj))
        url_col_name = getattr(url_sort_column_obj, 'value', str(url_sort_column_obj))
        error_info = f"Cursor sort column '{cursor_col_name}' does not match URL sort parameter '{url_col_name}'"
        logger.error(error_info)
        raise ValueError(error_info)
    
    logger.info(f"Cursor-sort validation passed. Both use column: {cursor_sort_column_obj}")

@router.get("", response_model=ReturnResponse)
async def search_domain(
    params: SearchDomainParams = Depends(),
    request: Request = None,  # Still needed for dynamic filter extraction
    db: AsyncSession = Depends(get_db),
    current_user = Security(get_current_user),
):
    """
    Pagination. Return list of domains with advanced filtering, sorting, and field selection.

    Query Params:
    - limit: int = 10 (number of items per page, max 1000)
    - cursor: str | None = None (Base64 encoded cursor for pagination)
    - sort: str = "-dom_last_seen" (sort by column, prefix with - for descending)
    - direction: str = "next" (pagination direction: "next" or "prev")
    - fields: str | None = None (comma-separated list of fields to return)
    - filters.{column}.{operation}: Dynamic filters (e.g., filters.status.eq=active)

    Supported filter operations: eq, lt, gt, neq, like

    Returns:
        {
            "status": "good|normal|error",
            "remark": "string",
            "data": {
                "page_data": {
                    "id": PaginationBase,
                    ...
                },
                "next_cursor": "string",
                "prev_cursor": "string"
            }
        }
    """
    
    try:
        # Parse and validate all parameters using Pydantic models
        sort_column, is_descending = params.parse_sort()
        cursor_data = params.parse_cursor()
        field_cols = params.parse_fields()
        
        # Extract and validate filters from request (dynamic query params)
        filters = DynamicFilters.from_request(request)

        # Convenience: support `search` or `q` query param as a domain_name substring search
        # If user passed ?search=google or ?q=.uk we translate it into filters.domain_name.like=<term>
        search_term = None
        if request is not None:
            search_term = request.query_params.get("search") or request.query_params.get("q")

        if search_term:
            # Sanitize the search term to prevent injection and invalid input
            try:
                search_term = InputSanitizer.sanitize_domain_search(search_term)
            except ValueError as e:
                logger.error(f"Invalid search term: {e}")
                return ReturnResponse(
                    status=ResponseStatus.error,
                    remark="Validation Error",
                    data={"error_detail": str(e), "error_code": 400}
                )

            # Get the domain_name column enum
            domain_col = FilterableColumns.find_column("domain_name")
            # If not configured as filterable, try to find via SortableColumns (fallback)
            if domain_col is None:
                domain_col = SortableColumns.find_column("domain_name")

            if domain_col is not None:
                # Only add if there's not already a domain_name filter
                already = any(getattr(c, 'value', None) == getattr(domain_col, 'value', None) for c in filters.filter_cols)
                if not already:
                    filters.filter_cols.append(domain_col)
                    filters.filter_ops.append(FilterOperations.LIKE)
                    filters.filter_values.append(search_term)
        
        # Handle direction logic: flip sort order for previous page
        query_is_descending = is_descending  # Original sort order for client
        if params.direction == "prev":
            # For previous page, flip the sort order in the backend query
            query_is_descending = not is_descending
            logger.info(f"Previous page requested: flipping sort order from {'DESC' if is_descending else 'ASC'} to {'DESC' if query_is_descending else 'ASC'}")
        else:
            logger.info(f"Next page requested: using original sort order {'DESC' if is_descending else 'ASC'}")

        # Store original cursor separately
        original_cursor = params.cursor if params.cursor is not None else None
        
        # Extract sort column object and value from cursor
        cursor_sort_column_obj, sort_cursor_value = extract_cursor_sort_info(cursor_data)
        
        # Validate cursor sort column matches URL sort parameter
        validate_cursor_with_sort(cursor_sort_column_obj, sort_column)

        # Log parsed parameters for debugging
        logger.info(f"Search parameters - Direction: {params.direction}, Sort: {sort_column} (original: {'DESC' if is_descending else 'ASC'}, query: {'DESC' if query_is_descending else 'ASC'}), FilterCols: {len(filters.filter_cols)}, FilterOps: {len(filters.filter_ops)}, FilterValues: {len(filters.filter_values)}, FieldCols: {len(field_cols)}, Cursor: {cursor_data}")
        
        # Call pagination service with validated parameters
        result = await get_paginated_response(
            db=db,
            limit=params.limit,
            sort_col=sort_column,
            is_desc=query_is_descending,  # Use the potentially flipped sort order
            filter_col=filters.filter_cols,
            filter_ops=filters.filter_ops,
            filter_val=filters.filter_values,
            sort_cursor_value=sort_cursor_value,
            field_cols=field_cols,
            after_id=cursor_data.get("domain_id") if cursor_data else None,
            cursor_data=cursor_data,  # Pass cursor_data for position tracking
            original_cursor=original_cursor  # Pass original cursor for prev_cursor
        )
        

        if result is None:
            logger.error("Pagination service returned None")
            return ReturnResponse(
                status=ResponseStatus.error,
                remark="Internal Server Error",
                data={"error_detail": "Pagination service failed", "error_code": 500}
            )
        
        # Check if result has at_data (DynamicPageReturnData) or not (PageReturnData)
        at_data = getattr(result, 'at_data', 1)
        total_data = getattr(result, 'total_data', 0)
        logger.info(f"Pagination successful - returned {len(result.page_data)} items, at_data={at_data}, total_data={total_data}")
        
        # Handle result ordering for direction
        if params.direction == "prev":
            # For previous page, reverse the order of items before sending to client
            # This ensures the items appear in the correct original sort order
            page_data = result.page_data
            if isinstance(page_data, dict):
                # Reverse the order of the dictionary items
                reversed_items = list(reversed(list(page_data.items())))
                result.page_data = dict(reversed_items)
                logger.info(f"Reversed page data order for previous page direction")
        
        # Encode cursors before returning
        result_dict = result.dict()
        
        # IMPORTANT: When direction=prev, we need to swap next_cursor and prev_cursor
        # because the data was fetched in reverse order
        if params.direction == "prev":
            # Get boundaries BEFORE swapping (use getattr in case of PageReturnData)
            at_data_val = result_dict.get("at_data", 1)
            total_data_val = result_dict.get("total_data", 0)
            
            # Log BEFORE swap
            logger.info(f"BEFORE swap - at_data={at_data_val}, prev_cursor={'null' if result_dict.get('prev_cursor') is None else 'present'}, next_cursor={'null' if result_dict.get('next_cursor') is None else 'present'}")
            
            # Swap the cursors for previous direction
            temp_next = result_dict.get("next_cursor")
            temp_prev = result_dict.get("prev_cursor")
            result_dict["next_cursor"] = temp_prev
            result_dict["prev_cursor"] = temp_next
            
            # CRITICAL: Only set prev_cursor to null if at first page
            if at_data_val <= params.limit:
                result_dict["prev_cursor"] = None
                logger.info(f"At first page (at_data={at_data_val} <= limit={params.limit}), forcing prev_cursor to null")
                # Do NOT set next_cursor to null here; keep it if there is more data
            logger.info(f"AFTER swap - at_data={at_data_val}, prev_cursor={'null' if result_dict.get('prev_cursor') is None else 'present'}, next_cursor={'null' if result_dict.get('next_cursor') is None else 'present'}")
        else:
            # For normal direction, also log the cursor states
            at_data_val = result_dict.get("at_data", 1)
            logger.info(f"Normal direction: at_data={at_data_val}, prev_cursor={'null' if result_dict.get('prev_cursor') is None else 'present'}, next_cursor={'null' if result_dict.get('next_cursor') is None else 'present'}")
        
        # Handle next_cursor encoding
        if result_dict.get("next_cursor"):
            try:
                # The cursor is currently a JSON string, we need to parse it and encode it properly
                import json
                next_cursor_data = json.loads(result_dict["next_cursor"])  # Use different variable name
                result_dict["next_cursor"] = encode_cursor(next_cursor_data)
            except Exception as e:
                logger.error(f"Error encoding next_cursor: {e}")
                result_dict["next_cursor"] = None
        
        # Handle prev_cursor encoding - it's also a JSON string that needs encoding
        if result_dict.get("prev_cursor"):
            try:
                import json
                prev_cursor_data = json.loads(result_dict["prev_cursor"])
                result_dict["prev_cursor"] = encode_cursor(prev_cursor_data)
            except Exception as e:
                logger.error(f"Error encoding prev_cursor: {e}")
                result_dict["prev_cursor"] = None
        
        return ReturnResponse(
            status=ResponseStatus.good,
            remark="Search successful",
            data=result_dict
        )

    except ValueError as e:
        # Handle validation errors (invalid sort, filter, or cursor)
        logger.error(f"Validation error in /search: {e}")
        return ReturnResponse(
            status=ResponseStatus.error,
            remark="Validation Error",
            data={"error_detail": str(e), "error_code": 400}
        )
    except Exception as e:
        logger.error(f"Error in /search: {e}")
        return ReturnResponse(
            status=ResponseStatus.error,
            remark="Internal Server Error",
            data={"error_code": 500}
        )


# =============================================================================
# FILTER EXAMPLES - All Available Filters
# =============================================================================
#
# DOMAIN FILTERS (domain table):
# ------------------------------
# Domain name (substring):
#   http://localhost:5252/search?filters.domain_name.like=google
#   http://localhost:5252/search?search=google  (shortcut)
#
# Domain name (exact):
#   http://localhost:5252/search?filters.domain_name.eq=example.com
#
# Domain status:
#   http://localhost:5252/search?filters.status=active
#   http://localhost:5252/search?filters.status=inactive
#   http://localhost:5252/search?filters.status.neq=unknown
#
# Last seen date:
#   http://localhost:5252/search?filters.last_seen.gt=2025-11-01
#   http://localhost:5252/search?filters.last_seen.lt=2025-12-01
#
# Source ID:
#   http://localhost:5252/search?filters.source_id=1
#   http://localhost:5252/search?filters.source_id.neq=5
#
# Is unrated:
#   http://localhost:5252/search?filters.is_unrated=true
#   http://localhost:5252/search?filters.is_unrated=false
#
#
# MALICIOUS FILTERS (domain_ip_malicious table):
# ----------------------------------------------
# Is malicious:
#   http://localhost:5252/search?filters.is_malicious=true
#   http://localhost:5252/search?filters.is_malicious=false
#   http://localhost:5252/search?filters.is_malicious.neq=true
#
#
# FAST FLUX FILTERS (fast_flux_analysis table):
# ---------------------------------------------
# Flux type (latest record only):
#   http://localhost:5252/search?filters.flux_type=single
#   http://localhost:5252/search?filters.flux_type=double
#   http://localhost:5252/search?filters.flux_type=name
#   http://localhost:5252/search?filters.flux_type=unknown
#   http://localhost:5252/search?filters.flux_type.neq=unknown
#
#
# SOURCE FILTERS (sources table):
# -------------------------------
# Source name:
#   http://localhost:5252/search?filters.source_name.like=phish
#   http://localhost:5252/search?filters.source_name.eq=openphish
#
#
# COMBINED FILTER EXAMPLES:
# -------------------------
# Active malicious domains:
#   http://localhost:5252/search?filters.status=active&filters.is_malicious=true
#
# Active domains with single flux:
#   http://localhost:5252/search?filters.status=active&filters.flux_type=single
#
# Malicious domains with fast flux:
#   http://localhost:5252/search?filters.is_malicious=true&filters.flux_type.neq=unknown
#
# Clean active domains (not malicious):
#   http://localhost:5252/search?filters.status=active&filters.is_malicious=false
#
# Unrated domains needing review:
#   http://localhost:5252/search?filters.is_unrated=true&filters.status=active
#
# Recently seen active threats:
#   http://localhost:5252/search?filters.status=active&filters.is_malicious=true&filters.last_seen.gt=2025-11-01
#
#
# SORTING & PAGINATION:
# ---------------------
# Sort by last seen (descending):
#   http://localhost:5252/search?sort=-dom_last_seen&limit=20
#
# Sort by domain name (ascending):
#   http://localhost:5252/search?sort=domain_name&limit=10
#
# With pagination cursor:
#   http://localhost:5252/search?cursor=base64encodedcursor&limit=10
#
#
# FIELD SELECTION:
# ----------------
# Return specific fields only:
#   http://localhost:5252/search?fields=domain_name,dom_last_seen,is_malicious,flux_type
#
# Full example with all features:
#   http://localhost:5252/search?limit=10&fields=domain_name,dom_last_seen,flux_type,is_malicious,dom_status&sort=-dom_last_seen&filters.status=active&filters.is_malicious=true
#
#
# FILTER OPERATIONS:
# ------------------
# eq  - Equal (default if not specified):       filters.status=active
# neq - Not equal:                               filters.flux_type.neq=unknown
# lt  - Less than:                               filters.last_seen.lt=2025-12-01
# gt  - Greater than:                            filters.last_seen.gt=2025-11-01
# like - Substring match (case-insensitive):     filters.domain_name.like=google
#
# =============================================================================