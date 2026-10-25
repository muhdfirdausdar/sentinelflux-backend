from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.domain_nameserver import DomainNameserver
from schemas.domain_nameserver import DomainNameserverColumn
from schemas.pagination import FilterOperations
from services.domain import DomainOrder
from utils.async_log import get_logger
from typing import List, Dict, Any
from schemas.domain_nameserver import DomainNSStats, DNSGetDataReturn
from services.tools.type_converter import safe_convert_cursor_values

logger = get_logger("services.nameserver_conn")


async def get_ns_con_data(
        db: AsyncSession,
        list_domain_ids: List[int] | None = None,
        requested_col: List[DomainNameserverColumn] | None = None,
) -> DNSGetDataReturn:
    """
    Reliable function to fetch paginated domain-nameserver data.
    Returns a dictionary mapping domain_id to DomainNSStats.
    
    Args:
        db: Database session
        list_domain_ids: Optional list of domain IDs to filter
        requested_col: List of columns to include (uses schema enum with aggregates)
    
    Returns:
        Dict[int, DomainNSStats]: Mapping domain_id to nameserver statistics
    """
    try:
        # Dynamic select based on requested_col
        select_columns = []
        has_aggregates = False
        
        if requested_col:
            # Always include domain_id for grouping
            select_columns.append(DomainNameserver.domain_id)
            
            for col in requested_col:
                if col == DomainNameserverColumn.COUNT_NS:
                    select_columns.append(func.count(DomainNameserver.nameserver_id).label("count_ns"))
                    has_aggregates = True
                elif col == DomainNameserverColumn.NS_AVERAGE_TTL:
                    select_columns.append(func.avg(DomainNameserver.ttl).label("ns_average_ttl"))
                    has_aggregates = True
                else:
                    # Regular column - handle aggregation for grouping
                    if has_aggregates or list_domain_ids:
                        # When using aggregates, we need to group by domain_id
                        # For other columns, use appropriate aggregate functions
                        if col == DomainNameserverColumn.FIRST_SEEN:
                            select_columns.append(func.min(DomainNameserver.first_seen).label("first_seen"))
                        elif col == DomainNameserverColumn.LAST_SEEN:
                            select_columns.append(func.max(DomainNameserver.last_seen).label("last_seen"))
                        elif col == DomainNameserverColumn.LOWEST_TTL:
                            select_columns.append(func.min(DomainNameserver.lowest_ttl).label("lowest_ttl"))
                        elif col == DomainNameserverColumn.HIGHEST_TTL:
                            select_columns.append(func.max(DomainNameserver.highest_ttl).label("highest_ttl"))
                        elif col == DomainNameserverColumn.LOWEST_TTL_TIME:
                            select_columns.append(func.min(DomainNameserver.lowest_ttl_time).label("lowest_ttl_time"))
                        elif col == DomainNameserverColumn.HIGHEST_TTL_TIME:
                            select_columns.append(func.max(DomainNameserver.highest_ttl_time).label("highest_ttl_time"))
                        elif col == DomainNameserverColumn.ID:
                            select_columns.append(func.array_agg(DomainNameserver.id).label("id_list"))
                        else:
                            # For other columns, just select them normally
                            select_columns.append(getattr(DomainNameserver, col.value))
                    else:
                        # No aggregates, select column directly
                        select_columns.append(getattr(DomainNameserver, col.value))
        
        if not select_columns:
            # Default columns with aggregation by domain
            select_columns = [
                DomainNameserver.domain_id,
                func.count(DomainNameserver.nameserver_id).label("count_ns"),
                func.avg(DomainNameserver.ttl).label("ns_average_ttl"),
                func.min(DomainNameserver.first_seen).label("first_seen"),
                func.max(DomainNameserver.last_seen).label("last_seen"),
                func.array_agg(DomainNameserver.id).label("id_list")
            ]
            has_aggregates = True

        # Build the query
        query = select(*select_columns)

        # Filter by domain_ids if provided
        if list_domain_ids:
            query = query.where(DomainNameserver.domain_id.in_(list_domain_ids))

        # Group by domain_id when using aggregate functions
        if has_aggregates:
            query = query.group_by(DomainNameserver.domain_id)

        # Execute query
        result = await db.execute(query)
        rows = result.all()

        # Process results into expected format
        domain_stats = {}
        for row in rows:
            domain_id = row.domain_id

            # Create stats dict for this domain
            stats_dict = {}

            # Add all available columns from row
            for col_name in row._fields:
                if col_name != 'domain_id':  # Skip domain_id as it's the key
                    value = getattr(row, col_name, None)
                    
                    # Handle special conversions
                    if col_name == 'ns_average_ttl' and value is not None:
                        stats_dict['average_ttl'] = float(value)  # Map to DomainNSStats field name
                    elif col_name == 'id_list' and value is not None:
                        stats_dict[col_name] = list(value)
                    else:
                        stats_dict[col_name] = value

            # Create DomainNSStats object
            domain_stats[domain_id] = DomainNSStats(**stats_dict)

        logger.info(f"Fetched nameserver connection data for {len(domain_stats)} domains")
        return domain_stats

    except Exception as e:
        logger.error(f"Error fetching domain nameserver connection data: {str(e)}")
        return {}

async def sort_domainns_with_cursor_paginate(
    db: AsyncSession,
    limit: int = 10,
    sort_col: DomainNameserverColumn | None = None, # col of item cursor and sort must be same
    sort_dir: str = "asc",
    sort_cursor_value: Any | None = None, 
    after_id: int | None = None,
    filter_query = None  # Optional filter query object to integrate
) -> List[int] | None:
    """
    Fetch a paginated list of unique domain IDs using cursor-based pagination.
    Supports both regular table columns and operational columns (count_ns, ns_average_ttl).
    
    For regular columns like last_seen, first_seen: uses appropriate aggregation (max/min) 
    to ensure one result per domain.
    For operational columns like count_ns, ns_average_ttl: already grouped by domain_id.
    
    Args:
        db: Database session
        limit: Number of items to fetch
        sort_col: Column to sort by (must match cursor value column)
        sort_dir: 'asc' or 'desc' for sorting direction
        sort_cursor_value: Value of the sort column from the last item of previous page
        after_id: domain_id of the last item from previous page (for stable pagination)
    
    Returns:
        List of unique domain IDs as integers or None on error
    """
    try:
        # Check if sort_col is an operational column
        is_operational = sort_col and DomainNameserverColumn.operations_col(sort_col.value)
        
        # Handle filter integration - need to restrict to filtered domain_ids
        filter_condition = None
        if filter_query is not None:
            # Execute filter query to get domain_ids, then use IN clause
            filter_result = await db.execute(filter_query)
            filter_rows = filter_result.all()
            filtered_domain_ids = [row[0] for row in filter_rows]
            
            if not filtered_domain_ids:
                # No domains match the filter
                return []
            
            filter_condition = DomainNameserver.domain_id.in_(filtered_domain_ids)
        
        # Build the base query and sort column reference
        if is_operational:
            # Handle operational columns with aggregation (already unique by domain)
            if sort_col == DomainNameserverColumn.COUNT_NS:
                aggregate_expr = func.count(DomainNameserver.nameserver_id)
            elif sort_col == DomainNameserverColumn.NS_AVERAGE_TTL:
                aggregate_expr = func.avg(DomainNameserver.ttl)
            else:
                # Fallback, shouldn't happen
                aggregate_expr = func.count(DomainNameserver.nameserver_id)
            
            # Create subquery for domain aggregates
            subq_select = select(
                DomainNameserver.domain_id,
                aggregate_expr.label('sort_value')
            )
            
            # Apply filter condition if exists
            if filter_condition is not None:
                subq_select = subq_select.where(filter_condition)
                
            subq = subq_select.group_by(DomainNameserver.domain_id).subquery()
            
            # Main query joining with subquery
            query = select(subq.c.domain_id)
            sort_column = subq.c.sort_value  # Reference for cursor and ordering
            
        else:
            # Handle regular columns - need aggregation to ensure unique domains
            if sort_col:
                # Determine appropriate aggregation based on column type
                if sort_col == DomainNameserverColumn.LAST_SEEN:
                    aggregate_expr = func.max(DomainNameserver.last_seen)
                elif sort_col == DomainNameserverColumn.FIRST_SEEN:
                    aggregate_expr = func.min(DomainNameserver.first_seen)
                elif sort_col == DomainNameserverColumn.LOWEST_TTL:
                    aggregate_expr = func.min(DomainNameserver.lowest_ttl)
                elif sort_col == DomainNameserverColumn.HIGHEST_TTL:
                    aggregate_expr = func.max(DomainNameserver.highest_ttl)
                elif sort_col == DomainNameserverColumn.LOWEST_TTL_TIME:
                    aggregate_expr = func.min(DomainNameserver.lowest_ttl_time)
                elif sort_col == DomainNameserverColumn.HIGHEST_TTL_TIME:
                    aggregate_expr = func.max(DomainNameserver.highest_ttl_time)
                elif sort_col == DomainNameserverColumn.TTL:
                    # For TTL, use average as it's more meaningful
                    aggregate_expr = func.avg(DomainNameserver.ttl)
                else:
                    # For other columns, use max as default
                    column_attr = getattr(DomainNameserver, sort_col.value)
                    aggregate_expr = func.max(column_attr)
                
                # Create subquery with domain aggregation
                subq_select = select(
                    DomainNameserver.domain_id,
                    aggregate_expr.label('sort_value')
                )
                
                # Apply filter condition if exists
                if filter_condition is not None:
                    subq_select = subq_select.where(filter_condition)
                    
                subq = subq_select.group_by(DomainNameserver.domain_id).subquery()
                
                query = select(subq.c.domain_id)
                sort_column = subq.c.sort_value
            else:
                # No sort column, just get unique domain_ids
                query = select(DomainNameserver.domain_id).distinct()
                
                # Apply filter condition if exists
                if filter_condition is not None:
                    query = query.where(filter_condition)
                    
                sort_column = None

        # Apply cursor logic (unified for both operational and regular columns)
        if sort_col and sort_cursor_value is not None and sort_column is not None:
            # Convert cursor values to appropriate types
            converted_cursor_value, converted_after_id, conversion_success = safe_convert_cursor_values(
                sort_cursor_value, after_id
            )
            
            if not conversion_success:
                logger.warning("Cursor value conversion failed, pagination may not work correctly")
                return None
            
            if sort_dir == "asc":
                if is_operational:
                    query = query.where(
                        or_(
                            sort_column > converted_cursor_value,
                            and_(
                                sort_column == converted_cursor_value,
                                subq.c.domain_id > converted_after_id if converted_after_id is not None else True
                            )
                        )
                    )
                else:
                    query = query.where(
                        or_(
                            sort_column > converted_cursor_value,
                            and_(
                                sort_column == converted_cursor_value,
                                subq.c.domain_id > converted_after_id if converted_after_id is not None else True
                            )
                        )
                    )
            else:
                if is_operational:
                    query = query.where(
                        or_(
                            sort_column < converted_cursor_value,
                            and_(
                                sort_column == converted_cursor_value,
                                subq.c.domain_id < converted_after_id if converted_after_id is not None else True
                            )
                        )
                    )
                else:
                    query = query.where(
                        or_(
                            sort_column < converted_cursor_value,
                            and_(
                                sort_column == converted_cursor_value,
                                subq.c.domain_id < converted_after_id if converted_after_id is not None else True
                            )
                        )
                    )

        # Apply ordering (unified for both operational and regular columns)
        order_expressions = []
        if sort_col and sort_column is not None:
            if sort_dir == "desc":
                order_expressions.append(sort_column.desc())
            else:
                order_expressions.append(sort_column.asc())
        
        # Always add domain_id as secondary sort for stable pagination
        if is_operational:
            if sort_dir == "desc":
                order_expressions.append(subq.c.domain_id.desc())
            else:
                order_expressions.append(subq.c.domain_id.asc())
        else:
            if sort_col:  # We have subquery
                if sort_dir == "desc":
                    order_expressions.append(subq.c.domain_id.desc())
                else:
                    order_expressions.append(subq.c.domain_id.asc())
            else:  # No sort, using distinct
                if sort_dir == "desc":
                    order_expressions.append(DomainNameserver.domain_id.desc())
                else:
                    order_expressions.append(DomainNameserver.domain_id.asc())
        
        query = query.order_by(*order_expressions).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        domain_ids = [row[0] for row in rows]
        return domain_ids

    except Exception as e:
        # Log error and return None
        logger.error(f"Error fetching unique domain id list from nameserver connections: {str(e)}")
        return None


    """
    Return Structure:
    [
        domain_id_1,
        domain_id_2,
        domain_id_3,
        ...
    ]
    Or None if error occurs
    
    Example:
    [
        1,
        5,
        12,
    ]
    
    Each item is a domain_id that matches the filter criteria
    and cursor pagination requirements.
    """