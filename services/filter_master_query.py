"""
Master query builder for multi-table filtering.
Builds efficient queries that return domain_ids based on filters across multiple tables.
"""

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Dict
from schemas.domain import DomainColumn
from schemas.domain_ip_connection import DomainIPConnectionColumn
from schemas.domain_nameserver import DomainNameserverColumn
from schemas.sources import Sources as SourcesColumn
from schemas.fast_flux_analysis import FastFluxAnalysisColumn
from schemas.domain_ip_malicious import DomIPMaliciousColumn
from models.domain import Domain
from models.domain_ip_connection import DomainIPConnection
from models.domain_nameserver import DomainNameserver
from models.domain_ip_malicious import DomainIPMalicious
from models.fast_flux_analysis import FastFluxAnalysis
from models.sources import Sources
from schemas.pagination import FilterOperations
from services.tools.type_converter import safe_convert_cursor_values
from utils.async_log import get_logger

logger = get_logger("services.filter_master_query")


async def build_domain_filter_query(
    db: AsyncSession,
    domain_filters: Dict[str, List]
):
    """
    Build query for domain table filters.
    Returns SQLAlchemy query object that selects domain_ids matching domain table filters.
    """
    try:
        if not domain_filters or not domain_filters.get('cols') or not domain_filters['cols']:
            logger.info(f"Domain filters check failed - domain_filters: {domain_filters}")
            return None
            
        query = select(Domain.id)
        
        filter_cols = domain_filters['cols']
        filter_ops = domain_filters['ops']
        filter_vals = domain_filters['vals']
        
        for i in range(len(filter_cols)):
            col_enum = filter_cols[i]
            operation = filter_ops[i]
            value = filter_vals[i]
            
            # Convert value to appropriate type
            converted_value, _, success = safe_convert_cursor_values(value, None)
            if not success:
                logger.warning(f"Failed to convert filter value: {value}")
                converted_value = value
            
            # Get column attribute
            column_attr = getattr(Domain, col_enum.value)
            
            # Apply filter condition based on operation
            if operation == FilterOperations.EQ:
                condition = column_attr == converted_value
            elif operation == FilterOperations.LT:
                condition = column_attr < converted_value
            elif operation == FilterOperations.GT:
                condition = column_attr > converted_value
            elif operation == FilterOperations.NEQ:
                condition = column_attr != converted_value
            elif operation == FilterOperations.LIKE:
                # Prefer case-insensitive match when supported by the DB
                try:
                    condition = column_attr.ilike(f"%{converted_value}%")
                except Exception:
                    condition = column_attr.like(f"%{converted_value}%")
            else:
                continue
                
            query = query.where(condition)
        
        logger.info(f"Domain filter query built successfully")
        return query
        
    except Exception as e:
        logger.error(f"Error building domain filter query: {str(e)}")
        return None


async def build_ip_conn_filter_query(
    db: AsyncSession,
    ip_conn_filters: Dict[str, List]
) -> List[int] | None:
    """
    Build query for domain_ip_connection table filters.
    Handles both regular columns and operational columns (count_ips, ips_average_ttl).
    Returns list of domain_ids that match IP connection filters.
    """
    try:
        if not ip_conn_filters or not ip_conn_filters.get('cols') or not ip_conn_filters['cols']:
            return None
            
        filter_cols = ip_conn_filters['cols']
        filter_ops = ip_conn_filters['ops']
        filter_vals = ip_conn_filters['vals']
        
        # Check if we have operational columns that need aggregation
        has_operational = any(
            col.value in ['count_ips', 'ips_average_ttl'] 
            for col in filter_cols
        )
        
        if has_operational:
            # Use aggregated query for operational columns
            query = select(DomainIPConnection.domain_id)
            
            # Add aggregated columns based on what's needed
            select_columns = [DomainIPConnection.domain_id]
            for col_enum in filter_cols:
                if col_enum.value == 'count_ips':
                    select_columns.append(func.count(DomainIPConnection.ip_id).label('count_ips'))
                elif col_enum.value == 'ips_average_ttl':
                    select_columns.append(func.avg(DomainIPConnection.ttl).label('ips_average_ttl'))
            
            query = select(*select_columns).group_by(DomainIPConnection.domain_id)
            
            # Apply filters including operational ones
            having_conditions = []
            where_conditions = []
            
            for i in range(len(filter_cols)):
                col_enum = filter_cols[i]
                operation = filter_ops[i]
                value = filter_vals[i]
                
                # Convert value
                converted_value, _, success = safe_convert_cursor_values(value, None)
                if not success:
                    converted_value = value
                
                if col_enum.value == 'count_ips':
                    # Use HAVING for aggregated column
                    if operation == FilterOperations.EQ:
                        having_conditions.append(func.count(DomainIPConnection.ip_id) == converted_value)
                    elif operation == FilterOperations.LT:
                        having_conditions.append(func.count(DomainIPConnection.ip_id) < converted_value)
                    elif operation == FilterOperations.GT:
                        having_conditions.append(func.count(DomainIPConnection.ip_id) > converted_value)
                    elif operation == FilterOperations.NEQ:
                        having_conditions.append(func.count(DomainIPConnection.ip_id) != converted_value)
                        
                elif col_enum.value == 'ips_average_ttl':
                    # Use HAVING for aggregated column
                    if operation == FilterOperations.EQ:
                        having_conditions.append(func.avg(DomainIPConnection.ttl) == converted_value)
                    elif operation == FilterOperations.LT:
                        having_conditions.append(func.avg(DomainIPConnection.ttl) < converted_value)
                    elif operation == FilterOperations.GT:
                        having_conditions.append(func.avg(DomainIPConnection.ttl) > converted_value)
                    elif operation == FilterOperations.NEQ:
                        having_conditions.append(func.avg(DomainIPConnection.ttl) != converted_value)
                        
                else:
                    # Regular column - use WHERE
                    column_attr = getattr(DomainIPConnection, col_enum.value)
                    if operation == FilterOperations.EQ:
                        where_conditions.append(column_attr == converted_value)
                    elif operation == FilterOperations.LT:
                        where_conditions.append(column_attr < converted_value)
                    elif operation == FilterOperations.GT:
                        where_conditions.append(column_attr > converted_value)
                    elif operation == FilterOperations.NEQ:
                        where_conditions.append(column_attr != converted_value)
                    elif operation == FilterOperations.LIKE:
                        try:
                            where_conditions.append(column_attr.ilike(f"%{converted_value}%"))
                        except Exception:
                            where_conditions.append(column_attr.like(f"%{converted_value}%"))
            
            # Apply WHERE conditions
            for condition in where_conditions:
                query = query.where(condition)
                
            # Apply HAVING conditions
            for condition in having_conditions:
                query = query.having(condition)
                
        else:
            # Simple query for regular columns only
            query = select(DomainIPConnection.domain_id).distinct()
            
            for i in range(len(filter_cols)):
                col_enum = filter_cols[i]
                operation = filter_ops[i]
                value = filter_vals[i]
                
                # Convert value
                converted_value, _, success = safe_convert_cursor_values(value, None)
                if not success:
                    converted_value = value
                
                # Get column attribute
                column_attr = getattr(DomainIPConnection, col_enum.value)
                
                # Apply filter condition
                if operation == FilterOperations.EQ:
                    condition = column_attr == converted_value
                elif operation == FilterOperations.LT:
                    condition = column_attr < converted_value
                elif operation == FilterOperations.GT:
                    condition = column_attr > converted_value
                elif operation == FilterOperations.NEQ:
                    condition = column_attr != converted_value
                elif operation == FilterOperations.LIKE:
                    try:
                        condition = column_attr.ilike(f"%{converted_value}%")
                    except Exception:
                        condition = column_attr.like(f"%{converted_value}%")
                else:
                    continue
                    
                query = query.where(condition)
        
        result = await db.execute(query)
        rows = result.all()
        domain_ids = [row[0] for row in rows]
        
        logger.info(f"IP connection filter returned {len(domain_ids)} domain IDs")
        return domain_ids
        
    except Exception as e:
        logger.error(f"Error in IP connection filter query: {str(e)}")
        return None


async def build_ns_conn_filter_query(
    db: AsyncSession,
    ns_conn_filters: Dict[str, List]
) -> List[int] | None:
    """
    Build query for domain_nameserver table filters.
    Handles both regular columns and operational columns (count_ns, ns_average_ttl).
    Returns list of domain_ids that match nameserver connection filters.
    """
    try:
        if not ns_conn_filters or not ns_conn_filters.get('cols') or not ns_conn_filters['cols']:
            return None
            
        filter_cols = ns_conn_filters['cols']
        filter_ops = ns_conn_filters['ops']
        filter_vals = ns_conn_filters['vals']
        
        # Check if we have operational columns that need aggregation
        has_operational = any(
            col.value in ['count_ns', 'ns_average_ttl'] 
            for col in filter_cols
        )
        
        if has_operational:
            # Use aggregated query for operational columns
            query = select(DomainNameserver.domain_id)
            
            # Add aggregated columns based on what's needed
            select_columns = [DomainNameserver.domain_id]
            for col_enum in filter_cols:
                if col_enum.value == 'count_ns':
                    select_columns.append(func.count(DomainNameserver.nameserver_id).label('count_ns'))
                elif col_enum.value == 'ns_average_ttl':
                    select_columns.append(func.avg(DomainNameserver.ttl).label('ns_average_ttl'))
            
            query = select(*select_columns).group_by(DomainNameserver.domain_id)
            
            # Apply filters including operational ones
            having_conditions = []
            where_conditions = []
            
            for i in range(len(filter_cols)):
                col_enum = filter_cols[i]
                operation = filter_ops[i]
                value = filter_vals[i]
                
                # Convert value
                converted_value, _, success = safe_convert_cursor_values(value, None)
                if not success:
                    converted_value = value
                
                if col_enum.value == 'count_ns':
                    # Use HAVING for aggregated column
                    if operation == FilterOperations.EQ:
                        having_conditions.append(func.count(DomainNameserver.nameserver_id) == converted_value)
                    elif operation == FilterOperations.LT:
                        having_conditions.append(func.count(DomainNameserver.nameserver_id) < converted_value)
                    elif operation == FilterOperations.GT:
                        having_conditions.append(func.count(DomainNameserver.nameserver_id) > converted_value)
                    elif operation == FilterOperations.NEQ:
                        having_conditions.append(func.count(DomainNameserver.nameserver_id) != converted_value)
                        
                elif col_enum.value == 'ns_average_ttl':
                    # Use HAVING for aggregated column
                    if operation == FilterOperations.EQ:
                        having_conditions.append(func.avg(DomainNameserver.ttl) == converted_value)
                    elif operation == FilterOperations.LT:
                        having_conditions.append(func.avg(DomainNameserver.ttl) < converted_value)
                    elif operation == FilterOperations.GT:
                        having_conditions.append(func.avg(DomainNameserver.ttl) > converted_value)
                    elif operation == FilterOperations.NEQ:
                        having_conditions.append(func.avg(DomainNameserver.ttl) != converted_value)
                        
                else:
                    # Regular column - use WHERE
                    column_attr = getattr(DomainNameserver, col_enum.value)
                    if operation == FilterOperations.EQ:
                        where_conditions.append(column_attr == converted_value)
                    elif operation == FilterOperations.LT:
                        where_conditions.append(column_attr < converted_value)
                    elif operation == FilterOperations.GT:
                        where_conditions.append(column_attr > converted_value)
                    elif operation == FilterOperations.NEQ:
                        where_conditions.append(column_attr != converted_value)
                    elif operation == FilterOperations.LIKE:
                        try:
                            where_conditions.append(column_attr.ilike(f"%{converted_value}%"))
                        except Exception:
                            where_conditions.append(column_attr.like(f"%{converted_value}%"))
            
            # Apply WHERE conditions
            for condition in where_conditions:
                query = query.where(condition)
                
            # Apply HAVING conditions
            for condition in having_conditions:
                query = query.having(condition)
                
        else:
            # Simple query for regular columns only
            query = select(DomainNameserver.domain_id).distinct()
            
            for i in range(len(filter_cols)):
                col_enum = filter_cols[i]
                operation = filter_ops[i]
                value = filter_vals[i]
                
                # Convert value
                converted_value, _, success = safe_convert_cursor_values(value, None)
                if not success:
                    converted_value = value
                
                # Get column attribute
                column_attr = getattr(DomainNameserver, col_enum.value)
                
                # Apply filter condition
                if operation == FilterOperations.EQ:
                    condition = column_attr == converted_value
                elif operation == FilterOperations.LT:
                    condition = column_attr < converted_value
                elif operation == FilterOperations.GT:
                    condition = column_attr > converted_value
                elif operation == FilterOperations.NEQ:
                    condition = column_attr != converted_value
                elif operation == FilterOperations.LIKE:
                    try:
                        condition = column_attr.ilike(f"%{converted_value}%")
                    except Exception:
                        condition = column_attr.like(f"%{converted_value}%")
                else:
                    continue
                    
                query = query.where(condition)
        
        result = await db.execute(query)
        rows = result.all()
        domain_ids = [row[0] for row in rows]
        
        logger.info(f"Nameserver connection filter returned {len(domain_ids)} domain IDs")
        return domain_ids
        
    except Exception as e:
        logger.error(f"Error in nameserver connection filter query: {str(e)}")
        return None


async def build_sources_filter_query(
    db: AsyncSession,
    sources_filters: Dict[str, List]
) -> List[int] | None:
    """
    Build query for sources table filters.
    Joins with domain table via source_id to return domain_ids.
    """
    try:
        if not sources_filters or not sources_filters.get('cols') or not sources_filters['cols']:
            return None
            
        # Join domain with sources via source_id
        query = select(Domain.id).join(Sources, Domain.source_id == Sources.id)
        
        filter_cols = sources_filters['cols']
        filter_ops = sources_filters['ops']
        filter_vals = sources_filters['vals']
        
        for i in range(len(filter_cols)):
            col_enum = filter_cols[i]
            operation = filter_ops[i]
            value = filter_vals[i]
            
            # Convert value
            converted_value, _, success = safe_convert_cursor_values(value, None)
            if not success:
                converted_value = value
            
            # Get column attribute from Sources table
            column_attr = getattr(Sources, col_enum.value)
            
            # Apply filter condition (mostly LIKE for source names)
            if operation == FilterOperations.EQ:
                condition = column_attr == converted_value
            elif operation == FilterOperations.NEQ:
                condition = column_attr != converted_value
            elif operation == FilterOperations.LIKE:
                try:
                    condition = column_attr.ilike(f"%{converted_value}%")
                except Exception:
                    condition = column_attr.like(f"%{converted_value}%")
            else:
                continue
                
            query = query.where(condition)
        
        result = await db.execute(query)
        rows = result.all()
        domain_ids = [row[0] for row in rows]
        
        logger.info(f"Sources filter returned {len(domain_ids)} domain IDs")
        return domain_ids
        
    except Exception as e:
        logger.error(f"Error in sources filter query: {str(e)}")
        return None


async def build_ff_analysis_filter_query(
    db: AsyncSession,
    ff_analysis_filters: Dict[str, List]
):
    """
    Build query for fast_flux_analysis table filters.
    Returns list of domain_ids matching fast flux filters (not a query object).
    
    IMPORTANT: Domains can have multiple flux_type records over time. This query
    only considers the MOST RECENT flux_type for each domain when filtering.
    
    Note: This function executes the query and returns domain IDs directly because
    the window function creates a CompoundSelect that doesn't support .intersect().
    """
    try:
        if not ff_analysis_filters or not ff_analysis_filters.get('cols') or not ff_analysis_filters['cols']:
            logger.info(f"Fast flux analysis filters check failed - ff_analysis_filters: {ff_analysis_filters}")
            return None
            
        filter_cols = ff_analysis_filters['cols']
        filter_ops = ff_analysis_filters['ops']
        filter_vals = ff_analysis_filters['vals']
        
        # Step 1: Create subquery to get the latest flux_type for each domain
        # This uses ROW_NUMBER() to rank records by detected_on DESC for each domain
        from sqlalchemy import func as sql_func
        
        # Subquery to get latest record per domain
        latest_flux_subquery = (
            select(
                FastFluxAnalysis.domain_id,
                FastFluxAnalysis.flux_type,
                sql_func.row_number().over(
                    partition_by=FastFluxAnalysis.domain_id,
                    order_by=FastFluxAnalysis.detected_on.desc()
                ).label('rn')
            )
            .subquery()
        )
        
        # Step 2: Filter to only get the most recent record (rn = 1) for each domain
        query = select(latest_flux_subquery.c.domain_id).where(
            latest_flux_subquery.c.rn == 1
        ).distinct()
        
        # Step 3: Apply user's filter conditions on the latest flux_type
        for i in range(len(filter_cols)):
            col_enum = filter_cols[i]
            operation = filter_ops[i]
            value = filter_vals[i]
            
            # Convert value to appropriate type
            converted_value, _, success = safe_convert_cursor_values(value, None)
            if not success:
                logger.warning(f"Failed to convert filter value: {value}")
                converted_value = value
            
            # Get column from subquery (only flux_type is available for filtering)
            if col_enum.value == 'flux_type':
                column_attr = latest_flux_subquery.c.flux_type
            else:
                logger.warning(f"Column {col_enum.value} not supported in latest flux filter")
                continue
            
            # Apply filter condition based on operation
            if operation == FilterOperations.EQ:
                condition = column_attr == converted_value
            elif operation == FilterOperations.LT:
                condition = column_attr < converted_value
            elif operation == FilterOperations.GT:
                condition = column_attr > converted_value
            elif operation == FilterOperations.NEQ:
                condition = column_attr != converted_value
            elif operation == FilterOperations.LIKE:
                # Prefer case-insensitive match when supported by the DB
                try:
                    condition = column_attr.ilike(f"%{converted_value}%")
                except Exception:
                    condition = column_attr.like(f"%{converted_value}%")
            else:
                logger.warning(f"Unsupported operation {operation} for fast flux analysis filter")
                continue
                
            query = query.where(condition)
        
        # CRITICAL FIX: Execute the query and return domain IDs as a list
        # The window function creates a CompoundSelect that doesn't support .intersect()
        # So we execute it here and return the IDs
        result = await db.execute(query)
        domain_ids = [row[0] for row in result.all()]
        
        logger.info(f"Fast flux analysis filter executed successfully (using LATEST flux_type per domain) - returned {len(domain_ids)} domains")
        return domain_ids
        
    except Exception as e:
        logger.error(f"Error building fast flux analysis filter query: {str(e)}")
        return None


async def build_dom_ip_mal_filter_query(
    db: AsyncSession,
    dom_ip_mal_filters: Dict[str, List]
):
    """
    Build query for domain_ip_malicious table filters.
    Returns SQLAlchemy query object for the operational 'is_malicious' column.
    """
    try:
        if not dom_ip_mal_filters or not dom_ip_mal_filters.get('cols') or not dom_ip_mal_filters['cols']:
            logger.info(f"Dom IP mal filters check failed - dom_ip_mal_filters: {dom_ip_mal_filters}")
            return None
            
        filter_cols = dom_ip_mal_filters['cols']
        filter_ops = dom_ip_mal_filters['ops']
        filter_vals = dom_ip_mal_filters['vals']
        
        # Since we typically have only one is_malicious filter, we'll handle the first one
        # If multiple filters exist, we'd need to combine them (but typically only one)
        
        for i in range(len(filter_cols)):
            col_enum = filter_cols[i]
            operation = filter_ops[i]
            value = filter_vals[i]
            
            if col_enum.value == 'is_malicious':
                # Handle the operational is_malicious column
                # Convert value (usually boolean for is_malicious)
                converted_value = None
                if isinstance(value, str):
                    if value.lower() in ['true', '1', 'yes']:
                        converted_value = True
                    elif value.lower() in ['false', '0', 'no']:
                        converted_value = False
                else:
                    converted_value = bool(value)
                
                if operation == FilterOperations.EQ:
                    if converted_value is True:
                        # Return domains that have AT LEAST ONE malicious IP
                        query = select(DomainIPConnection.domain_id).distinct().join(
                            DomainIPMalicious, 
                            DomainIPConnection.id == DomainIPMalicious.domain_ip_id
                        )
                    else:
                        # Return domains that have NO malicious IPs at all
                        # Use subquery to find domains with malicious IPs, then exclude them
                        malicious_domains_subquery = (
                            select(DomainIPConnection.domain_id).distinct()
                            .join(DomainIPMalicious, DomainIPConnection.id == DomainIPMalicious.domain_ip_id)
                            .scalar_subquery()
                        )
                        # Get all domains from domain_ip_connection that are NOT in the malicious list
                        query = select(DomainIPConnection.domain_id).distinct().where(
                            ~DomainIPConnection.domain_id.in_(malicious_domains_subquery)
                        )
                        
                elif operation == FilterOperations.NEQ:
                    if converted_value is True:
                        # Return domains that are NOT malicious (have NO malicious IPs)
                        malicious_domains_subquery = (
                            select(DomainIPConnection.domain_id).distinct()
                            .join(DomainIPMalicious, DomainIPConnection.id == DomainIPMalicious.domain_ip_id)
                            .scalar_subquery()
                        )
                        query = select(DomainIPConnection.domain_id).distinct().where(
                            ~DomainIPConnection.domain_id.in_(malicious_domains_subquery)
                        )
                    else:
                        # Return domains that ARE malicious (have AT LEAST ONE malicious IP)
                        query = select(DomainIPConnection.domain_id).distinct().join(
                            DomainIPMalicious, 
                            DomainIPConnection.id == DomainIPMalicious.domain_ip_id
                        )
                else:
                    logger.warning(f"Unsupported operation {operation} for is_malicious column")
                    continue
                    
                logger.info(f"Domain IP malicious filter query built successfully")
                return query
                    
            else:
                # Handle other columns in DomainIPMalicious if they exist
                logger.warning(f"Column {col_enum.value} not supported in DomainIPMalicious filters")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error building domain IP malicious filter query: {str(e)}")
        return None


async def build_master_filtered_domain_query(
    db: AsyncSession,
    domain_filters: Dict[str, List] | None = None,
    ip_conn_filters: Dict[str, List] | None = None,
    ns_conn_filters: Dict[str, List] | None = None,
    sources_filters: Dict[str, List] | None = None,
    ff_analysis_filters: Dict[str, List] | None = None,
    dom_ip_mal_filters: Dict[str, List] | None = None
):
    """
    Master function to build a combined filter query.
    Returns a SQLAlchemy query object that selects domain_ids matching ALL filter criteria.
    Uses INTERSECT to combine results from different tables (AND logic).
    """
    try:
        logger.info("Building master filtered domain query from all tables")
        logger.info(f"Received filters - domain: {domain_filters}, ip_conn: {ip_conn_filters}, ns_conn: {ns_conn_filters}, sources: {sources_filters}, ff_analysis: {ff_analysis_filters}, dom_ip_mal: {dom_ip_mal_filters}")
        
        # Collect query objects from each table's filters
        filter_queries = []
        
        # Build queries for each table that has filters
        if domain_filters:
            domain_query = await build_domain_filter_query(db, domain_filters)
            if domain_query is not None:
                filter_queries.append(domain_query)
        
        # TODO: Add other filter query builders when ready
        # if ip_conn_filters:
        #     ip_conn_query = await build_ip_conn_filter_query(db, ip_conn_filters)
        #     if ip_conn_query is not None:
        #         filter_queries.append(ip_conn_query)
        
        if dom_ip_mal_filters:
            dom_ip_mal_query = await build_dom_ip_mal_filter_query(db, dom_ip_mal_filters)
            if dom_ip_mal_query is not None:
                filter_queries.append(dom_ip_mal_query)
        
        if ff_analysis_filters:
            ff_analysis_result = await build_ff_analysis_filter_query(db, ff_analysis_filters)
            if ff_analysis_result is not None:
                # ff_analysis returns a list of domain IDs, not a query object
                # Convert it to a simple select query that can be intersected
                if isinstance(ff_analysis_result, list):
                    if ff_analysis_result:  # Only if list is not empty
                        from models.domain import Domain
                        ff_analysis_query = select(Domain.id).where(Domain.id.in_(ff_analysis_result))
                        filter_queries.append(ff_analysis_query)
                    else:
                        # Empty list means no matches - return empty result
                        logger.info("Fast flux filter returned no matches")
                        from models.domain import Domain
                        return select(Domain.id).where(Domain.id == -1)  # Impossible condition
                else:
                    filter_queries.append(ff_analysis_result)
        
        # If no filters provided, return None (no filtering)
        if not filter_queries:
            logger.info("No filter queries built, returning None")
            return None
        
        # If only one filter, return it directly
        if len(filter_queries) == 1:
            logger.info("Single filter query built")
            return filter_queries[0]
        
        # Combine multiple queries using INTERSECT (AND logic)
        # CRITICAL: Use SQLAlchemy's intersect() function that can handle multiple queries
        # The .intersect() method on query objects only works for 2 queries, and returns
        # a CompoundSelect that doesn't support further .intersect() calls
        from sqlalchemy import intersect
        
        combined_query = intersect(*filter_queries)
        
        logger.info(f"Combined filter query built with {len(filter_queries)} filter tables")
        return combined_query
        
    except Exception as e:
        logger.error(f"Error building master filter query: {str(e)}")
        return None