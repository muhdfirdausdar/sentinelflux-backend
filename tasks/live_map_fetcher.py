"""
PLAN:
- Create redis cache keys type of hash to store client session data
- Have one function to handle the logic of storing and retrieving session data
- Make sure at start of function, we need to remove the client registry that have
    last_connected older than 5 minutes


"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy import text
from database import engine
from utils.async_log import get_logger


logger = get_logger("live_map_fetcher")

# Global cache to prevent multiple simultaneous DB queries
_last_query_time: Optional[datetime] = None
_query_lock = asyncio.Lock()
_cached_result: Optional[Tuple] = None
_min_query_interval = timedelta(seconds=5)  # Minimum 5 seconds between DB queries


async def fetch_latest_live_map_data(
    last_update: Optional[datetime] = None,
    domain_id: Optional[int] = None
) -> Tuple[Optional[Dict], Optional[str], Optional[int]]:
    """
    Fetch latest records from live_fast_flux_view table.
    
    This function includes rate limiting to prevent multiple concurrent clients
    from hammering the database with simultaneous queries.
    
    Args:
        last_update: Last update timestamp to fetch records after (optional)
        domain_id: Domain ID to exclude from results (optional)
        Both params must be provided together or both None
    
    Returns:
        Tuple of (combined_data_dict, latest_update_timestamp, latest_domain_id)
        
        Example return structure:
        (
            {
                "domain_id": {
                    "102.165.0.1": {
                        "last_active": "2025-10-12 06:30:00.123456",
                        "latitude": 3.139,
                        "longitude": 101.6869,
                        "country": "Malaysia",
                        "flux_type": "single"
                    },
                    "102.165.0.1": {
                        "last_active": "2025-10-12 06:30:00.123456",
                        "latitude": 3.139,
                        "longitude": 101.6869,
                        "country": "Malaysia",
                        "flux_type": "single"
                    }
                },
                "domain_id_2": {
                    "172.67.23.45": {
                        "last_active": "2025-10-11 21:00:00.789012",
                        "latitude": 37.751,
                        "longitude": -97.822,
                        "country": "United States",
                        "flux_type": "double"
                    }
                },
                "domain_id_3": {
                  "89.144.11.99": {
                      "last_active": "2025-10-12 07:58:07.188208",
                      "latitude": 47.816845,
                      "longitude": 9.061462,
                      "country": "Germany",
                      "flux_type": "double"
                  }
                }
            },
            "2025-10-12 21:14:04.730609",  # Latest updated_at as string
            140996  # Latest domain_id
        )
        
        Returns (None, None, None) if no records found
    """
    global _last_query_time, _cached_result
    
    # Rate limiting: Check if we should skip this query
    async with _query_lock:
        current_time = datetime.utcnow()
        
        # If a query was made recently, return cached result or skip
        if _last_query_time and (current_time - _last_query_time) < _min_query_interval:
            time_since_last = (current_time - _last_query_time).total_seconds()
            logger.debug(
                f"Rate limit: Skipping query (last query {time_since_last:.2f}s ago, "
                f"minimum interval: {_min_query_interval.total_seconds()}s)"
            )
            # Return cached result if available, otherwise return None
            if _cached_result:
                return _cached_result
            return None, None, None
        
        # Update last query time
        _last_query_time = current_time
    
    try:
        # Validate params: both must be None or both must be provided
        if (last_update is None) != (domain_id is None):
            raise ValueError("Both last_update and domain_id must be provided together or both None")
        
        async with engine.begin() as conn:
            # Case 1: Both params are None - fetch all records
            if last_update is None and domain_id is None:
                query = text("""
                    SELECT domain_id, flux_type, last_active, total_ips, geojson, updated_at
                    FROM live_fast_flux_view
                    ORDER BY updated_at ASC
                """)
                result = await conn.execute(query)
            
            # Case 2: Both params provided - fetch records after last_update, excluding the specific domain_id
            else:
                query = text("""
                    SELECT domain_id, flux_type, last_active, total_ips, geojson, updated_at
                    FROM live_fast_flux_view
                    WHERE (updated_at > :last_update)
                       
                    ORDER BY updated_at ASC, domain_id ASC
                """)
                result = await conn.execute(
                    query,
                    {"last_update": last_update, "domain_id": domain_id}
                )
            
            # Fetch all rows
            rows = result.fetchall()
            
            # If no data found, cache and return None
            if not rows:
                logger.info("No new records found in live_fast_flux_view")
                result_tuple = (None, None, None)
                _cached_result = result_tuple
                return result_tuple
            
            # Build the combined data dictionary grouped by domain_id
            combined_data = {}
            
            for row in rows:
                domain_id = str(row.domain_id)  # Convert to string for consistent key type
                flux_type = row.flux_type
                geojson = row.geojson
                
                # Initialize domain_id entry if not exists
                if domain_id not in combined_data:
                    combined_data[domain_id] = {}
                
                # Process each IP in the geojson and add flux_type from the record
                if geojson and isinstance(geojson, dict):
                    for ip_address, geo_data in geojson.items():
                        # Add flux_type to each IP's data and keep datetime as string
                        ip_entry = {
                            "last_active": geo_data.get("last_active"),
                            "latitude": geo_data.get("latitude"),
                            "longitude": geo_data.get("longitude"),
                            "country": geo_data.get("country"),
                            "flux_type": flux_type
                        }
                        combined_data[domain_id][ip_address] = ip_entry
            
            # Get the latest update timestamp and domain_id from the last row (since sorted by updated_at ASC)
            latest_update_timestamp = str(rows[-1].updated_at)
            latest_domain_id = rows[-1].domain_id
            
            logger.info(
                f"Fetched {len(rows)} records with {len(combined_data)} unique domains. "
                f"Latest update: {latest_update_timestamp}, domain_id: {latest_domain_id}"
            )
            
            # Cache the result
            result_tuple = (combined_data, latest_update_timestamp, latest_domain_id)
            _cached_result = result_tuple
            
            return result_tuple
    
    except Exception as e:
        logger.error(f"Error fetching live map data: {e}")
        raise

