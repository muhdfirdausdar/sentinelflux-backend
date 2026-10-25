from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from models.domain_ip_malicious import DomainIPMalicious
from models.domain_ip_connection import DomainIPConnection
from typing import List, Dict
from utils.async_log import get_logger

logger = get_logger("services.dom_ip_mal")

async def check_is_malicious(
    db: AsyncSession, 
    domain_ids: List[int],
    source_id: int | None = None,
    malicious_type_id: int | None = None
) -> Dict[int, bool]:
    """
    Check if domain IDs are marked as malicious in the domain_ip_malicious table.
    
    Args:
        db: Database session
        domain_ids: List of domain IDs to check
        source_id: Optional source filter
        malicious_type_id: Optional malicious type filter
    
    Returns:
        Dict mapping domain_id to boolean (True if malicious, False if not)
        Example: {1: True, 2: False, 3: True}
    """
    try:
        if not domain_ids:
            logger.warning("Empty domain_ids list provided")
            return {}
        
        # Build query to find malicious domain IDs
        # Join with domain_ip_connection to get domain_id from domain_ip_malicious
        query = (
            select(distinct(DomainIPConnection.domain_id))
            .select_from(DomainIPMalicious)
            .join(DomainIPConnection, DomainIPMalicious.domain_ip_id == DomainIPConnection.id)
            .where(DomainIPConnection.domain_id.in_(domain_ids))
        )
        
        # Apply optional filters
        if source_id is not None:
            query = query.where(DomainIPMalicious.source_id == source_id)
        
        if malicious_type_id is not None:
            query = query.where(DomainIPMalicious.malicious_type_id == malicious_type_id)
        
        # Execute query
        result = await db.execute(query)
        malicious_domain_ids = set(result.scalars().all())
        
        # Build result dictionary
        result_dict = {}
        for domain_id in domain_ids:
            result_dict[domain_id] = domain_id in malicious_domain_ids
        
        logger.info(f"Checked maliciousness for {len(domain_ids)} domains, found {len(malicious_domain_ids)} malicious")
        return result_dict
        
    except Exception as e:
        logger.error(f"Error checking domain maliciousness: {str(e)}")
        raise

"""
Usage Examples:

Basic usage - check if domains are malicious:
    result = await check_is_malicious(db, [1, 2, 3, 4, 5])
    # Returns: {1: True, 2: False, 3: True, 4: False, 5: False}

Filter by specific source:
    result = await check_is_malicious(db, [1, 2, 3], source_id=10)
    # Returns: {1: True, 2: False, 3: False} - only malicious entries from source 10

Filter by malicious type:
    result = await check_is_malicious(db, [1, 2, 3], malicious_type_id=2)
    # Returns: {1: False, 2: True, 3: False} - only malicious entries of type 2

Combine filters:
    result = await check_is_malicious(db, [1, 2, 3], source_id=10, malicious_type_id=2)
    # Returns: {1: False, 2: True, 3: False} - malicious entries from source 10 AND type 2

The function:
1. Takes a list of domain IDs and checks if they appear in domain_ip_malicious table
2. Uses JOIN with domain_ip_connection to map domain_ip_id back to domain_id
3. Returns a dictionary with all requested domain IDs mapped to True/False
4. Supports optional filtering by source_id and malicious_type_id
5. Uses DISTINCT to avoid duplicate domain IDs if a domain has multiple malicious entries
6. Handles empty input gracefully and provides comprehensive logging
"""
