
from typing import Any, Dict, List
from schemas.pagination import FieldTable, FilterableColumns, SortableColumns, PageReturnData, DynamicPageReturnData, PaginationBase, FastFluxType
from schemas.domain import DomainColumn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime
import json
from utils.async_log import get_logger
from services.domain import  get_domain_data, sort_domain_with_cursor_paginate
from services.sources import get_source_name
from services.ips_conn import get_ips_con_data, sort_ipsconn_with_cursor_paginate
from services.nameserver_conn import get_ns_con_data, sort_domainns_with_cursor_paginate
from services.dom_ip_mal import check_is_malicious
from services.fast_flux_analysis import get_domain_flux_types
from services.get_fields_data import get_fields_data, generate_next_cursor, generate_cursors_for_page
from services.tools.paginate_utils import categorize_filters_and_sort, get_filter_summary, get_sort_summary

logger = get_logger("services.pagination")
from services.filter_master_query import build_master_filtered_domain_query 


async def get_total_filtered_count(db: AsyncSession, filter_query) -> int:
    """
    Get the total count of filtered data without pagination limit.
    
    Args:
        db: Database session
        filter_query: The filter query object from build_master_filtered_domain_query
    
    Returns:
        int: Total count of filtered results
    """
    try:
        if filter_query is None:
            # No filters, count all domains
            from models.domain import Domain
            count_query = select(func.count(Domain.id))
            result = await db.execute(count_query)
            total_count = result.scalar()
        else:
            # Count the filtered results
            # Convert the filter_query to a count query
            count_query = select(func.count()).select_from(filter_query.subquery())
            result = await db.execute(count_query)
            total_count = result.scalar()
        
        logger.info(f"Total filtered count: {total_count}")
        return total_count or 0
    except Exception as e:
        logger.error(f"Error getting total filtered count: {e}")
        return 0


async def calculate_current_position(
    db: AsyncSession, 
    filter_query,
    sort_table: str,
    sort_column_enum,
    sort_dir: str,
    sort_cursor_value: Any,
    after_id: int,
    current_page_domain_ids: List[int],
    cursor_data: dict = None
) -> int:
    """
    Calculate the current position (at_data) by using cursor position or defaulting to 1.
    
    Args:
        db: Database session
        filter_query: Filter query object
        sort_table: Which table the sort column belongs to
        sort_column_enum: Sort column enum
        sort_dir: Sort direction ("asc" or "desc")
        sort_cursor_value: Current cursor value
        after_id: ID after which to start counting
        current_page_domain_ids: IDs of the current page (to find the first one)
        cursor_data: Parsed cursor data containing position info
    
    Returns:
        int: Current position (1-based)
    """
    try:
        if not current_page_domain_ids:
            return 1
        
        # If cursor contains position info, use it
        if cursor_data and "next_item_pos" in cursor_data:
            try:
                position = int(cursor_data["next_item_pos"])
                logger.info(f"Using cursor position: {position}")
                return position
            except (ValueError, TypeError):
                logger.warning("Invalid next_item_pos in cursor, using default")
        
        # If no cursor, this is the first page
        if sort_cursor_value is None and after_id is None:
            return 1
        
        # For legacy cursors without next_item_pos info, default to 1
        # Future enhancement: could estimate position by counting records
        logger.info("Legacy cursor detected, using default position 1")
        return 1
        
    except Exception as e:
        logger.error(f"Error calculating current position: {e}")
        return 1



def determine_cursors(
    current_cursor: str | None,
    next_cursor: str | None,
    at_data: int,
    limit: int,
    total_data: int
) -> tuple[str | None, str | None]:
    """
    Determine prev_cursor and next_cursor based on current position and page boundaries.
    
    Args:
        current_cursor: The cursor that was sent by client (original cursor)
        next_cursor: Generated next cursor
        at_data: Current position in dataset (1-based)
        limit: Page size
        total_data: Total count of all filtered data
    
    Returns:
        tuple: (prev_cursor, next_cursor)
    """
    # Determine prev_cursor
    # prev_cursor is the original cursor that client sent (only if not at start)
    if at_data <= limit:
        # At start of dataset (page 1: showing items 1 to limit)
        prev_cursor = None
    else:
        # Not at start, use the original cursor client sent as prev_cursor
        prev_cursor = current_cursor
    
    # Determine next_cursor
    # Check if we're at the end of dataset
    if at_data + limit - 1 >= total_data:
        # At end of dataset (last page)
        next_cursor = None
    # else: keep the generated next_cursor as is
    
    return prev_cursor, next_cursor


async def get_paginated_response(
    db: AsyncSession,
    limit: int = 10,
    sort_col: str | None = None,
    is_desc: bool = False,
    filter_col: List | None = None,
    filter_ops: List | None = None,
    filter_val: List | None = None,
    sort_cursor_value: Any | None = None,
    field_cols: List | None = None,
    after_id: int | None = None,
    cursor_data: dict | None = None,  # Add cursor_data parameter
    original_cursor: str | None = None  # Add original_cursor parameter
):  
    
    try:
        """
            We have 5 different tables to pull data from:
            1. Domain, function in services/domain.py, schema in schemas/domain.py
            2. Sources, function in services/sources.py, schema in schemas/sources.py
            3. Domain IP Connection, function in services/ips_conn.py, schema in schemas/domain_ip_connection.py
            4. Domain Nameserver Connection, function in services/ns_conn.py, schema in schemas/domain_nameserver.py
            5. Domain IP Malicious, function in services/dom_ip_mal.py, schema in schemas/domain_ip_mal.py

            Step:
            1. Separate and group the filter_* into their respective tables
            - use .table() to check which table the column belongs to
            - each group have three list var with
            - eg: domain_filter_col, domain_filter_ops, domain_filter_val . The type of first list is based on the schema class column, second on use the pagination enum operation
            - do same for other tables
            2. Separate and categorize the sort_col based on table
            - check if sort_col is in domain, sources, ip_conn, ns_conn, or dom_ip_mal
            - later we will do first mandatory info searching using sort column
            3. Do domain id fetching based on sort and cursor info, for from three tables
            domain, domain_ip_connection and domain_nameserver
        """
        sort_dir = "asc"
        if is_desc is True:
            sort_dir = "desc"
        
        

        
        # Separating and categorizing filters and sort columns based on table

        # Use utility function to categorize filters and sort
        categorized_data = categorize_filters_and_sort(
            filter_col=filter_col,
            filter_ops=filter_ops,
            filter_val=filter_val,
            sort_col=sort_col
        )

        # Extract categorized data for easier access
        domain_filters = categorized_data['domain_filters']
        ip_conn_filters = categorized_data['ip_conn_filters']
        ns_conn_filters = categorized_data['ns_conn_filters']
        sources_filters = categorized_data['sources_filters']
        ff_analysis_filters = categorized_data['ff_analysis_filters']
        dom_ip_mal_filters = categorized_data['dom_ip_mal_filters']

        sort_table = categorized_data['sort_table']
        sort_column_enum = categorized_data['sort_column_enum']
        # Note that the cursor second item should be same as sort col, just pass the value as sort value for cursor pagination

        # Log categorization results for debugging
        logger.info(f"Sort table: {sort_table}, Sort column: {sort_column_enum}")
        logger.info(f"Filter summary: {get_filter_summary(categorized_data)}")
        logger.info(f"Sort summary: {get_sort_summary(categorized_data)}")

        # Apply multi-table filters before sorting
        filter_query = await build_master_filtered_domain_query(
            db=db,
            domain_filters=domain_filters,
            ip_conn_filters=ip_conn_filters,
            ns_conn_filters=ns_conn_filters,
            sources_filters=sources_filters,
            ff_analysis_filters=ff_analysis_filters,
            dom_ip_mal_filters=dom_ip_mal_filters
        )
        
        logger.info(f"Filter query object: {filter_query}")
        if filter_query is not None:
            logger.info("Filter query built successfully - will be passed to sorting function")
            # For debugging, we can execute the query to see how many results it would return
            debug_result = await db.execute(filter_query)
            debug_rows = debug_result.all()
            debug_ids = [row[0] for row in debug_rows]
            logger.info(f"Filter query would return {len(debug_ids)} domain IDs")
            logger.debug(f"First 10 domain IDs: {debug_ids[:10] if len(debug_ids) > 0 else 'None'}")
        else:
            logger.info("No filters applied - will use all domains")



        # Step 3: Fetch domain IDs based on sort and cursor info
        if sort_table == "domain":
            domain_ids = await sort_domain_with_cursor_paginate(
                db=db,
                limit=limit,
                sort_col=sort_column_enum,
                sort_dir=sort_dir,
                sort_cursor_value=sort_cursor_value,
                after_id=after_id,
                filter_query=filter_query
            )
            logger.info(f"Domain IDs from domain table: {len(domain_ids)} results")
            logger.debug(f"Domain IDs order: {domain_ids}")
            
        elif sort_table == "domain_ip_connection":
            domain_ids = await sort_ipsconn_with_cursor_paginate(
                db=db,
                limit=limit,
                sort_col=sort_column_enum,
                sort_dir=sort_dir,
                sort_cursor_value=sort_cursor_value,
                after_id=after_id,
                filter_query=filter_query
            )
            logger.info(f"Domain IDs from IP connection table: {len(domain_ids)} results")
            logger.debug(f"Domain IDs order (ip_conn): {domain_ids}")
            
        elif sort_table == "domain_nameserver":
            domain_ids = await sort_domainns_with_cursor_paginate(
                db=db,
                limit=limit,
                sort_col=sort_column_enum,
                sort_dir=sort_dir,
                sort_cursor_value=sort_cursor_value,
                after_id=after_id,
                filter_query=filter_query
            )
            logger.info(f"Domain IDs from nameserver connection table: {len(domain_ids)} results")
            logger.debug(f"Domain IDs order (ns_conn): {domain_ids}")
            
        else:
            logger.error(f"Unsupported sort table: {sort_table}")
            domain_ids = None




        # Step 4: Get total count of filtered data (before pagination)
        total_count = await get_total_filtered_count(db, filter_query)
        
        # Step 5: Calculate current position
        current_position = await calculate_current_position(
            db=db,
            filter_query=filter_query,
            sort_table=sort_table,
            sort_column_enum=sort_column_enum,
            sort_dir=sort_dir,
            sort_cursor_value=sort_cursor_value,
            after_id=after_id,
            current_page_domain_ids=domain_ids,
            cursor_data=cursor_data
        )


        # Step 6: Get fields data using the new get_fields_data module
        if domain_ids and field_cols:
            fields_result = await get_fields_data(
                db=db,
                domain_ids=domain_ids,
                field_cols=field_cols,
                sort_column=sort_column_enum,
                sort_cursor_value=sort_cursor_value
            )
            
            # Generate both next and prev cursors using new method
            # Get the page data and domain IDs
            page_data_dict = fields_result.get("page_data", {})
            domain_ids_list = list(page_data_dict.keys())

            # Safety check: ensure the returned page is ordered according to the requested sort column
            # Sometimes upstream queries or joins may return IDs in an unexpected order; enforce ordering here.
            try:
                sort_key = sort_column_enum.aliases if hasattr(sort_column_enum, 'aliases') else 'dom_last_seen'
                # Build list of tuples (domain_id, sort_value) using page data
                sortable_list = []
                for did in domain_ids_list:
                    row = page_data_dict.get(did, {})
                    val = row.get(sort_key)
                    sortable_list.append((did, val))

                # Detect if ordering is already correct (non-increasing for desc, non-decreasing for asc)
                def is_monotonic(lst, desc: bool):
                    prev = None
                    for _, v in lst:
                        if v is None:
                            # treat None as smallest possible value
                            current = float('-inf') if desc else float('inf')
                        else:
                            current = v
                        if prev is not None:
                            if desc and current > prev:
                                return False
                            if not desc and current < prev:
                                return False
                        prev = current
                    return True

                already_desc = is_monotonic([(d, v) for d, v in sortable_list], desc=(sort_dir == 'desc'))
                if not already_desc:
                    # Re-sort domain_ids_list by sort_value and tie-break by domain id
                    reverse = (sort_dir == 'desc')
                    # When values are None, place them at the end for desc, start for asc
                    def key_fn(item):
                        did, val = item
                        # Normalize None to a comparable value
                        if val is None:
                            # For descending, None should be very small so it appears at the end
                            return (float('-inf') if reverse else float('inf'), int(did))
                        return (val, int(did))

                    sorted_items = sorted(sortable_list, key=key_fn, reverse=reverse)
                    domain_ids_list = [did for did, _ in sorted_items]
                    # Rebuild page_data_dict in the sorted order (preserve insertion order)
                    new_page_data = {}
                    for did in domain_ids_list:
                        new_page_data[did] = page_data_dict.get(did)
                    page_data_dict = new_page_data
                    logger.info(f"Reordered page by sort key '{sort_key}' to enforce sort direction {sort_dir}")
            except Exception as e:
                logger.warning(f"Unable to enforce page ordering safeguard: {e}")
            
            # Generate cursors from current page boundaries
            next_cursor, prev_cursor = generate_cursors_for_page(
                page_data_dict=page_data_dict,
                domain_ids=domain_ids_list,
                sort_column=sort_column_enum,
                current_position=current_position,
                page_size=len(domain_ids)
            )
            
            # Apply boundary logic to cursors
            # For first page: no prev_cursor
            if current_position <= limit:
                prev_cursor = None
            
            # For last page: no next_cursor 
            if current_position + limit - 1 >= total_count:
                next_cursor = None
            
            logger.info(f"Generated dynamic page data for {fields_result.get('data_count', 0)} domains")

            # Convert page_data_dict (domain_id -> row) into an ordered list of
            # items [{id: domain_id, ...fields}, ...] to preserve ordering in JSON
            ordered_page_list = []
            for did in domain_ids_list:
                row = page_data_dict.get(did, {})
                item = {"id": did}
                # Merge row fields into item
                if isinstance(row, dict):
                    item.update(row)
                ordered_page_list.append(item)

            return DynamicPageReturnData(
                page_data=ordered_page_list,
                data_count=fields_result.get("data_count", 0),
                total_data=total_count,
                at_data=current_position,
                next_cursor=next_cursor,
                prev_cursor=prev_cursor
            )
        else:
            logger.warning("No domain IDs or field columns provided")
            return PageReturnData(page_data={}, next_cursor=None)

    except Exception as e:
        logger.error(f"Error in pagination: {str(e)}")
        raise RuntimeError(f"Error in pagination: {str(e)}")