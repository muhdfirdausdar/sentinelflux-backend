"""
Get fields data module for pagination.
Fetches data from multiple tables based on requested field columns and domain IDs.
Returns data in dynamic Pydantic models that only contain the requested fields.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel
from schemas.pagination import PaginationBase, FastFluxType, FieldTable
from schemas.domain import DomainColumn, DomainStatus
from schemas.domain_ip_connection import DomainIPConnectionColumn
from schemas.domain_nameserver import DomainNameserverColumn
from schemas.sources import Sources as SourcesColumn
from schemas.fast_flux_analysis import FastFluxAnalysisColumn
from schemas.domain_ip_malicious import DomIPMaliciousColumn
from services.domain import get_domain_data
from services.sources import get_source_name
from services.ips_conn import get_ips_con_data
from services.nameserver_conn import get_ns_con_data
from services.dom_ip_mal import check_is_malicious
from services.fast_flux_analysis import get_domain_flux_types
from services.tools.dynamic_model_builder import (
    create_dynamic_pagination_model_from_cols, 
    convert_single_to_dynamic_model
)
from utils.async_log import get_logger
from datetime import datetime

logger = get_logger("services.get_fields_data")


def categorize_field_columns(field_cols: List) -> Dict[str, List]:
    """
    Categorize field columns by their source table.
    Returns a dictionary with lists of columns needed from each table.
    """
    categorized = {
        'domain_cols': [],
        'ip_conn_cols': [],
        'ns_conn_cols': [],
        'sources_cols': [],
        'ff_analysis_cols': [],
        'dom_ip_mal_cols': []
    }
    
    for field_col in field_cols:
        # Check which table this field belongs to
        if hasattr(field_col, 'table'):
            table_name = field_col.table
            
            if table_name == "domain":
                categorized['domain_cols'].append(field_col)
            elif table_name == "domain_ip_connection":
                categorized['ip_conn_cols'].append(field_col)
            elif table_name == "domain_nameserver":
                categorized['ns_conn_cols'].append(field_col)
            elif table_name == "sources":
                categorized['sources_cols'].append(field_col)
            elif table_name == "fast_flux_analysis":
                categorized['ff_analysis_cols'].append(field_col)
            elif table_name == "domain_ip_malicious":
                categorized['dom_ip_mal_cols'].append(field_col)
        else:
            # Fallback: try to determine by column enum type
            if isinstance(field_col, DomainColumn):
                categorized['domain_cols'].append(field_col)
            elif isinstance(field_col, DomainIPConnectionColumn):
                categorized['ip_conn_cols'].append(field_col)
            elif isinstance(field_col, DomainNameserverColumn):
                categorized['ns_conn_cols'].append(field_col)
            elif isinstance(field_col, SourcesColumn):
                categorized['sources_cols'].append(field_col)
            elif isinstance(field_col, FastFluxAnalysisColumn):
                categorized['ff_analysis_cols'].append(field_col)
            elif isinstance(field_col, DomIPMaliciousColumn):
                categorized['dom_ip_mal_cols'].append(field_col)
    
    return categorized


def get_required_domain_columns(field_cols: List) -> List[DomainColumn]:
    """
    Determine which domain columns are needed based on requested fields.
    Always includes essential columns for PaginationBase.
    """
    required_cols = set()
    
    # Always include essential columns
    required_cols.add(DomainColumn.ID)
    required_cols.add(DomainColumn.DOMAIN_NAME)
    required_cols.add(DomainColumn.LAST_SEEN)
    required_cols.add(DomainColumn.STATUS)
    required_cols.add(DomainColumn.IS_UNRATED)  # Needed for is_unrated field
    required_cols.add(DomainColumn.SOURCE_ID)  # Needed for source name lookup
    
    # Add specific domain columns if requested
    for field_col in field_cols:
        if hasattr(field_col, 'table') and field_col.table == "domain":
            if field_col == DomainColumn.FIRST_SEEN:
                required_cols.add(DomainColumn.FIRST_SEEN)
            # Add other domain columns as needed
    
    return list(required_cols)


def get_required_ip_conn_columns(field_cols: List) -> List[DomainIPConnectionColumn]:
    """
    Determine which IP connection columns are needed based on requested fields.
    """
    required_cols = set()
    
    # Check if any IP-related fields are requested
    ip_fields_requested = any(
        hasattr(field_col, 'table') and field_col.table == "domain_ip_connection"
        for field_col in field_cols
    )
    
    if ip_fields_requested:
        # Add operational columns that are commonly needed
        required_cols.add(DomainIPConnectionColumn.COUNT_IPS)
        required_cols.add(DomainIPConnectionColumn.IPS_AVERAGE_TTL)
        required_cols.add(DomainIPConnectionColumn.LAST_SEEN)
        required_cols.add(DomainIPConnectionColumn.LOWEST_TTL)
        required_cols.add(DomainIPConnectionColumn.LOWEST_TTL_TIME)
        required_cols.add(DomainIPConnectionColumn.HIGHEST_TTL)
        required_cols.add(DomainIPConnectionColumn.HIGHEST_TTL_TIME)
        required_cols.add(DomainIPConnectionColumn.ID)  # For ID list aggregation
    
    return list(required_cols)


def get_required_ns_conn_columns(field_cols: List) -> List[DomainNameserverColumn]:
    """
    Determine which nameserver connection columns are needed based on requested fields.
    """
    required_cols = set()
    
    # Check if any NS-related fields are requested
    ns_fields_requested = any(
        hasattr(field_col, 'table') and field_col.table == "domain_nameserver"
        for field_col in field_cols
    )
    
    if ns_fields_requested:
        # Add operational columns that are commonly needed
        required_cols.add(DomainNameserverColumn.COUNT_NS)
        required_cols.add(DomainNameserverColumn.NS_AVERAGE_TTL)
        required_cols.add(DomainNameserverColumn.LAST_SEEN)
        required_cols.add(DomainNameserverColumn.LOWEST_TTL)
        required_cols.add(DomainNameserverColumn.LOWEST_TTL_TIME)
        required_cols.add(DomainNameserverColumn.HIGHEST_TTL)
        required_cols.add(DomainNameserverColumn.HIGHEST_TTL_TIME)
        required_cols.add(DomainNameserverColumn.ID)  # For ID list aggregation
    
    return list(required_cols)


async def get_fields_data(
    db: AsyncSession,
    domain_ids: List[int],
    field_cols: List,
    sort_column = None,
    sort_cursor_value: Any = None
) -> Dict[str, Any]:
    """
    Fetch comprehensive data for the requested fields from all relevant tables.
    Returns dynamic Pydantic models containing only the requested fields.
    
    Args:
        db: Database session
        domain_ids: List of domain IDs to fetch data for
        field_cols: List of field column enums indicating what data to fetch
        sort_column: The sort column used (for cursor generation)
        sort_cursor_value: Current cursor value (for next cursor generation)
    
    Returns:
        Dict[str, Any]: Dictionary with "data" (list of model instances) and "data_count" keys
    """
    try:
        logger.info(f"Fetching fields data for {len(domain_ids)} domains")
        
        if not domain_ids:
            return {"page_data": [], "data_count": 0}

        # Create dynamic model based on requested fields
        field_names = [col.aliases for col in field_cols]
        DynamicModel = create_dynamic_pagination_model_from_cols(field_cols)
        
        # Determine required columns for each table
        domain_cols = get_required_domain_columns(field_cols)
        ip_conn_cols = get_required_ip_conn_columns(field_cols)
        ns_conn_cols = get_required_ns_conn_columns(field_cols)
        
        # Fetch domain data (always needed)
        domain_data = await get_domain_data(
            db=db,
            list_ids=domain_ids,
            requested_col=domain_cols
        )
        
        if not domain_data:
            logger.warning("No domain data found")
            return {"page_data": [], "data_count": 0}
        
        # Extract source_ids for source name lookup
        source_ids = {}
        for domain_id, data in domain_data.items():
            if "source_id" in data:
                source_ids[domain_id] = data["source_id"]
        
        # Get source names for all unique source_ids in batch
        unique_source_ids = [sid for sid in set(source_ids.values()) if sid is not None]
        source_names_result = await get_source_name(db=db, source_id=unique_source_ids) if unique_source_ids else {}
        source_names = source_names_result if isinstance(source_names_result, dict) else {}
        
        # Fetch IP connection statistics if needed
        ip_stats = {}
        if ip_conn_cols:
            ip_stats_result = await get_ips_con_data(
                db=db,
                list_domain_ids=domain_ids,
                requested_col=ip_conn_cols
            )
            ip_stats = ip_stats_result if isinstance(ip_stats_result, dict) else {}
        
        # Fetch nameserver connection statistics if needed
        ns_stats = {}
        if ns_conn_cols:
            ns_stats_result = await get_ns_con_data(
                db=db,
                list_domain_ids=domain_ids,
                requested_col=ns_conn_cols
            )
            ns_stats = ns_stats_result if isinstance(ns_stats_result, dict) else {}
        
        # Get malicious status (always check for is_malicious field)
        malicious_status = await check_is_malicious(db=db, domain_ids=domain_ids)
        if not isinstance(malicious_status, dict):
            malicious_status = {}
        
        # Get fast flux types (always check for fast_flux_type field)
        flux_types = await get_domain_flux_types(db=db, domain_ids=domain_ids)
        if not isinstance(flux_types, dict):
            flux_types = {}

        # Build pagination data
        dynamic_data = []
        for domain_id in domain_ids:
            data = domain_data.get(domain_id)
            if not data:
                continue
                
            # Get associated data for this domain
            domain_ip_stats = ip_stats.get(domain_id)
            domain_ns_stats = ns_stats.get(domain_id)
            
            # Get source name for this domain's source_id
            domain_source_id = source_ids.get(domain_id)
            domain_source_name = source_names.get(domain_source_id) if domain_source_id else None
            
            # Get malicious status and flux type for this domain
            domain_is_malicious = malicious_status.get(domain_id, False)
            domain_flux_type = flux_types.get(domain_id, "Unknown")
            
            # Map flux type string to FastFluxType enum
            flux_type_mapping = {
                "single": FastFluxType.single,
                "double": FastFluxType.double,
                "name": FastFluxType.name,
                "unknown": FastFluxType.unknown,
                "Unknown": FastFluxType.unknown
            }
            mapped_flux_type = flux_type_mapping.get(domain_flux_type, FastFluxType.none)
            
            # Create full PaginationBase object first
            full_pagination_item = PaginationBase(
                id=domain_id,
                domain_name=data.get("domain_name", ""),
                dom_last_seen=data.get("last_seen", datetime.now()),
                dom_status=data.get("status", DomainStatus.UNKNOWN),
                is_malicious=domain_is_malicious,
                source_name=domain_source_name,  # Changed from source_domain to source_name (alias)
                is_unrated=data.get("is_unrated", False),

                # IP statistics from get_ips_con_data (using alias field names)
                num_ips=domain_ip_stats.count_ips if domain_ip_stats and hasattr(domain_ip_stats, 'count_ips') else 0,
                domip_avg_ttl=int(domain_ip_stats.average_ttl) if domain_ip_stats and hasattr(domain_ip_stats, 'average_ttl') and domain_ip_stats.average_ttl else 0,
                domip_last_seen=domain_ip_stats.last_seen if domain_ip_stats and hasattr(domain_ip_stats, 'last_seen') else None,
                domip_lowest_ttl=domain_ip_stats.lowest_ttl if domain_ip_stats and hasattr(domain_ip_stats, 'lowest_ttl') else None,
                domip_low_ttl_seen=domain_ip_stats.lowest_ttl_time if domain_ip_stats and hasattr(domain_ip_stats, 'lowest_ttl_time') else None,
                domip_highest_ttl=domain_ip_stats.highest_ttl if domain_ip_stats and hasattr(domain_ip_stats, 'highest_ttl') else None,
                domip_high_ttl_seen=domain_ip_stats.highest_ttl_time if domain_ip_stats and hasattr(domain_ip_stats, 'highest_ttl_time') else None,

                # NS statistics from get_ns_con_data (using alias field names)
                num_ns=domain_ns_stats.count_ns if domain_ns_stats and hasattr(domain_ns_stats, 'count_ns') else 0,
                domns_avg_ttl=int(domain_ns_stats.average_ttl) if domain_ns_stats and hasattr(domain_ns_stats, 'average_ttl') and domain_ns_stats.average_ttl else 0,
                domns_last_seen=domain_ns_stats.last_seen if domain_ns_stats and hasattr(domain_ns_stats, 'last_seen') else None,
                domns_lowest_ttl=domain_ns_stats.lowest_ttl if domain_ns_stats and hasattr(domain_ns_stats, 'lowest_ttl') else None,
                domns_low_ttl_seen=domain_ns_stats.lowest_ttl_time if domain_ns_stats and hasattr(domain_ns_stats, 'lowest_ttl_time') else None,
                domns_highest_ttl=domain_ns_stats.highest_ttl if domain_ns_stats and hasattr(domain_ns_stats, 'highest_ttl') else None,
                domns_high_ttl_seen=domain_ns_stats.highest_ttl_time if domain_ns_stats and hasattr(domain_ns_stats, 'highest_ttl_time') else None,

                # Fast flux type
                flux_type=mapped_flux_type
            )
            
            # Convert to dynamic model with only requested fields (plus id)
            field_names_with_id = field_names + ['id']  # Always include id for response structure
            dynamic_item = convert_single_to_dynamic_model(full_pagination_item, DynamicModel, field_names_with_id)
            dynamic_data.append(dynamic_item)
        
        logger.info(f"Successfully built dynamic pagination data for {len(dynamic_data)} domains")
        
        # Convert list to dictionary with domain_id as keys
        page_data_dict = {}
        for item in dynamic_data:
            if hasattr(item, 'id') and item.id is not None:
                # Extract only the fields (exclude id from the nested object)
                item_dict = item.model_dump()
                domain_id = item_dict.pop('id')  # Remove id from the nested object
                page_data_dict[domain_id] = item_dict
            elif hasattr(item, 'domain_name'):
                # Fallback: use domain_name if id not available (shouldn't happen)
                item_dict = item.model_dump()
                page_data_dict[item.domain_name] = item_dict

        # Debug: log sort column values for each domain in the returned page (helps verify ordering)
        try:
            sort_key = sort_column.aliases if hasattr(sort_column, 'aliases') else 'dom_last_seen'
            debug_values = []
            for did in domain_ids:
                row = page_data_dict.get(did, {})
                val = row.get(sort_key)
                debug_values.append((did, val))
            logger.debug(f"Page sort values (domain_id, {sort_key}): {debug_values}")
        except Exception:
            # Non-fatal; continue to return data
            pass

        return {
            "page_data": page_data_dict,
            "data_count": len(page_data_dict)
        }
        
    except Exception as e:
        logger.error(f"Error fetching fields data: {str(e)}")
        return {"page_data": [], "data_count": 0}


def generate_next_cursor(
    data_list: List,  # Can be BaseModel objects or dictionaries
    sort_column = None
) -> str | None:
    """
    Generate next cursor for pagination based on the last item in the results.
    
    Args:
        data_list: List of dynamic model instances or dictionaries in sort order
        sort_column: The column used for sorting
    
    Returns:
        JSON string for next cursor or None if no more pages
    """
    try:
        if not data_list:
            return None
            
        # Get the last item
        last_data = data_list[-1]
        
        if not last_data:
            return None
        
        # Build cursor based on sort column
        cursor_dict = {}
        
        # Check if last_data is a dictionary or object
        is_dict = isinstance(last_data, dict)
        
        # Always include ID if available
        if is_dict:
            # For dictionary, look for 'id' key
            if 'id' in last_data:
                cursor_dict["domain_id"] = last_data['id']
        else:
            # For object, look for 'id' attribute
            if hasattr(last_data, 'id'):
                cursor_dict["domain_id"] = last_data.id
        
        if sort_column:
            # Use the sort column's alias as the cursor key
            cursor_key = sort_column.aliases
            
            # Dynamically get the value from last_data using the alias
            try:
                if is_dict:
                    cursor_value = last_data.get(cursor_key)
                else:
                    cursor_value = getattr(last_data, cursor_key, None)
                
                # Handle datetime objects by converting to ISO format
                if hasattr(cursor_value, 'isoformat'):
                    cursor_value = cursor_value.isoformat()
                # Handle enum objects by getting their value
                elif hasattr(cursor_value, 'value'):
                    cursor_value = cursor_value.value
                
                if cursor_value is not None:
                    cursor_dict[cursor_key] = cursor_value
                else:
                    # Fallback to dom_last_seen if field not found
                    fallback_value = last_data.get('dom_last_seen') if is_dict else getattr(last_data, 'dom_last_seen', None)
                    if fallback_value and hasattr(fallback_value, 'isoformat'):
                        cursor_dict["dom_last_seen"] = fallback_value.isoformat()
            except (AttributeError, KeyError):
                # Fallback to dom_last_seen if attribute doesn't exist
                logger.warning(f"Field '{cursor_key}' not found in data, using dom_last_seen as fallback")
                fallback_value = last_data.get('dom_last_seen') if is_dict else getattr(last_data, 'dom_last_seen', None)
                if fallback_value and hasattr(fallback_value, 'isoformat'):
                    cursor_dict["dom_last_seen"] = fallback_value.isoformat()
        else:
            # No sort column, use dom_last_seen as default if available
            fallback_value = last_data.get('dom_last_seen') if is_dict else getattr(last_data, 'dom_last_seen', None)
            if fallback_value and hasattr(fallback_value, 'isoformat'):
                cursor_dict["dom_last_seen"] = fallback_value.isoformat()
        
        # Convert to JSON string (will be base64 encoded by the route handler)
        import json
        return json.dumps(cursor_dict)
        
    except Exception as e:
        logger.error(f"Error generating next cursor: {str(e)}")
        return None


def generate_cursors_for_page(
    page_data_dict: Dict[int, Dict],
    domain_ids: List[int],
    sort_column = None,
    current_position: int = 1,
    page_size: int = 10
) -> tuple[str | None, str | None]:
    """
    Generate both next and prev cursors for pagination based on current page boundaries.
    
    Args:
        page_data_dict: Dictionary of domain_id -> data dict
        domain_ids: List of domain IDs corresponding to page_data_dict
        sort_column: The column used for sorting
        current_position: Current position in the dataset (1-based)
        page_size: Number of items in current page
    
    Returns:
        tuple: (next_cursor, prev_cursor) - both as JSON strings or None
    """
    try:
        if not page_data_dict or not domain_ids:
            return None, None
        
        def create_cursor(domain_id: int, data: dict, position: int) -> str | None:
            """Helper to create a cursor from domain data"""
            cursor_dict = {
                "domain_id": domain_id,
                "next_item_pos": position
            }
            
            if sort_column:
                cursor_key = sort_column.aliases
                cursor_value = data.get(cursor_key)
                
                # Handle datetime objects by converting to ISO format
                if hasattr(cursor_value, 'isoformat'):
                    cursor_value = cursor_value.isoformat()
                # Handle enum objects by getting their value
                elif hasattr(cursor_value, 'value'):
                    cursor_value = cursor_value.value
                
                if cursor_value is not None:
                    cursor_dict[cursor_key] = cursor_value
                else:
                    # Fallback to dom_last_seen if field not found
                    fallback_value = data.get('dom_last_seen')
                    if fallback_value and hasattr(fallback_value, 'isoformat'):
                        cursor_dict["dom_last_seen"] = fallback_value.isoformat()
            else:
                # No sort column, use dom_last_seen as default if available
                fallback_value = data.get('dom_last_seen')
                if fallback_value and hasattr(fallback_value, 'isoformat'):
                    cursor_dict["dom_last_seen"] = fallback_value.isoformat()
            
            import json
            return json.dumps(cursor_dict)
        
        # Generate next_cursor from LAST row of current page
        last_domain_id = domain_ids[-1]
        last_data = page_data_dict.get(last_domain_id)
        next_cursor = None
        if last_data:
            next_position = current_position + page_size
            next_cursor = create_cursor(last_domain_id, last_data, next_position)
        
        # Generate prev_cursor from FIRST row of current page  
        first_domain_id = domain_ids[0]
        first_data = page_data_dict.get(first_domain_id)
        prev_cursor = None
        if first_data:
            prev_position = max(1, current_position - page_size)
            prev_cursor = create_cursor(first_domain_id, first_data, prev_position)
        
        logger.info(f"Generated cursors - next: {bool(next_cursor)}, prev: {bool(prev_cursor)}")
        return next_cursor, prev_cursor
        
    except Exception as e:
        logger.error(f"Error generating cursors: {str(e)}")
        return None, None


def generate_next_cursor_with_id(
    page_data_dict: Dict[int, Dict],
    domain_ids: List[int],
    sort_column = None,
    current_position: int = 1,
    page_size: int = 10
) -> str | None:
    """
    Legacy function - now uses the new cursor generation method.
    Returns only the next_cursor for backward compatibility.
    """
    next_cursor, _ = generate_cursors_for_page(
        page_data_dict, domain_ids, sort_column, current_position, page_size
    )
    return next_cursor
