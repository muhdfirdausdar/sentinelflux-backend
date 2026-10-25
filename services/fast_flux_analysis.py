from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.fast_flux_analysis import FastFluxAnalysis, FastFluxType
from typing import List, Dict
from utils.async_log import get_logger

logger = get_logger("services.fast_flux_analysis")

async def get_domain_flux_types(
    db: AsyncSession, 
    domain_ids: List[int]
) -> Dict[int, str]:
    """
    Get flux types for domain IDs from the fast_flux_analysis table.
    
    Args:
        db: Database session
        domain_ids: List of domain IDs to check
    
    Returns:
        Dict mapping domain_id to flux_type string
        - If domain exists in table: returns actual flux_type ('single', 'double', 'name', 'unknown')
        - If domain not in table: returns 'Unknown'
        Example: {1: 'single', 2: 'Unknown', 3: 'double'}
    """
    try:
        if not domain_ids:
            logger.warning("Empty domain_ids list provided")
            return {}
        
        # Query to get ONLY the LATEST flux type for each domain
        # When a domain has multiple flux_type records, only return the most recent one
        # This ensures consistency with the filter logic
        from sqlalchemy import func as sql_func
        
        # Use ROW_NUMBER() to get the latest record per domain
        latest_flux_subquery = (
            select(
                FastFluxAnalysis.domain_id,
                FastFluxAnalysis.flux_type,
                sql_func.row_number().over(
                    partition_by=FastFluxAnalysis.domain_id,
                    order_by=FastFluxAnalysis.detected_on.desc()
                ).label('rn')
            )
            .where(FastFluxAnalysis.domain_id.in_(domain_ids))
            .subquery()
        )
        
        # Select only records where rn = 1 (latest record)
        query = select(
            latest_flux_subquery.c.domain_id,
            latest_flux_subquery.c.flux_type
        ).where(latest_flux_subquery.c.rn == 1)
        
        # Execute query
        result = await db.execute(query)
        flux_data = result.fetchall()
        
        # Create mapping of domain_id to flux_type (now only one per domain)
        found_domains = {}
        for row in flux_data:
            domain_id, flux_type = row
            found_domains[domain_id] = flux_type
        
        logger.debug(f"Flux type selection - Using LATEST flux_type per domain (by detected_on DESC)")
        
        # Build result dictionary - include all requested domains
        result_dict = {}
        for domain_id in domain_ids:
            if domain_id in found_domains:
                result_dict[domain_id] = found_domains[domain_id]
            else:
                result_dict[domain_id] = "Unknown"
        
        logger.info(f"Fetched flux types for {len(domain_ids)} domains, found {len(found_domains)} with analysis")
        return result_dict
        
    except Exception as e:
        logger.error(f"Error fetching domain flux types: {str(e)}")
        raise

"""
Usage Examples:

Basic usage - get flux types for domains:
    result = await get_domain_flux_types(db, [1, 2, 3, 4, 5])
    # Returns: {1: 'single', 2: 'Unknown', 3: 'double', 4: 'Unknown', 5: 'name'}

Check single domain:
    result = await get_domain_flux_types(db, [100])
    # Returns: {100: 'single'} or {100: 'Unknown'} if not analyzed

Empty list handling:
    result = await get_domain_flux_types(db, [])
    # Returns: {}

The function:
1. Takes a list of domain IDs and fetches their flux_type from fast_flux_analysis table
2. Returns a dictionary mapping each domain_id to its flux_type
3. Domains not found in the table are marked as 'Unknown'
4. Ensures all requested domain IDs are included in the result
5. Handles empty input gracefully and provides comprehensive logging

Possible flux_type values:
- 'single': Single flux detected
- 'double': Double flux detected  
- 'name': Name flux detected
- 'unknown': Analyzed but type is unknown
- 'Unknown': Domain not analyzed (not in fast_flux_analysis table)
"""
