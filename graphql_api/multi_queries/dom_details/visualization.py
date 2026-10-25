"""
Visualization Multi-Query for Domain Details
IP hopping visualization - groups historical IP records by time windows
"""
from typing import Optional, List, Dict, Set
from datetime import datetime, timedelta
import strawberry
from strawberry.types import Info
import hashlib
import json

from ...types.dom_details.visualization import (
    IPHoppingVisualization, IPHoppingTimeGroup, IPLocation
)

# Import existing query classes
from ...queries.history_dom_ip_conn import HistoryDomainIPConnectionQuery
from ...queries.history_geoip import HistoryGeoIPQuery
from ...queries.ip import IPQuery


@strawberry.type
class VisualizationQuery:
    """Multi-query for domain visualization"""

    @strawberry.field
    async def ip_hopping_visualization(
        self,
        info: Info,
        domain_id: int,
        days_back: int = 30
    ) -> Optional[IPHoppingVisualization]:
        """
        Get IP hopping visualization data for a domain
        
        Groups historical domain-IP connection records into time windows (±3 minutes).
        Records within the same 3-minute window are considered from the same DNS query.
        Fetches geolocation for each IP at the time it was recorded.
        Skips duplicate groups (same IPs and locations as previous group).
        
        Parameters:
        - domain_id: The domain to visualize
        - days_back: Number of days to look back (default: 30)
        
        GraphQL Query Example:
        
        {
          ipHoppingVisualization(domainId: 5, daysBack: 30) {
            domainId
            timeGroups {
              timestamp
              ips {
                ipAddress
                latitude
                longitude
              }
            }
          }
        }
        
        Returns:
        - Grouped IP records with geolocation at each time point
        - Only includes groups that are different from the previous one
        """
        
        # ===== 1. Get Historical Domain-IP Connection Records =====
        history_query = HistoryDomainIPConnectionQuery()
        
        # Calculate datetime range
        from datetime import timezone as dt_timezone
        current_time = datetime.now(dt_timezone.utc)
        from_datetime = current_time - timedelta(days=days_back)
        
        # Fetch all history records for this domain (oldest to latest)
        history_records = await history_query.history_domain_ip_connections(
            info=info,
            domain_id=domain_id,
            from_datetime=from_datetime.isoformat(),
            until_datetime=current_time.isoformat()
        )
        
        if not history_records:
            return IPHoppingVisualization(
                domain_id=domain_id,
                time_groups=[]
            )
        
        # Sort by updated_at ascending (oldest first)
        history_records.sort(key=lambda r: r.updated_at)
        
        # ===== 2. Group Records by Time Windows (±3 minutes) =====
        time_window = timedelta(minutes=3)
        groups: List[Dict] = []
        current_group: List = []
        current_group_start: Optional[datetime] = None
        
        for record in history_records:
            record_time = record.updated_at
            
            # Start a new group or add to current group
            if current_group_start is None:
                # First record - start new group
                current_group_start = record_time
                current_group.append(record)
            elif abs((record_time - current_group_start).total_seconds()) <= 180:  # 3 minutes = 180 seconds
                # Within 3 minutes of group start - add to current group
                current_group.append(record)
            else:
                # Outside 3-minute window - finalize current group and start new one
                if current_group:
                    # Get latest datetime in this group
                    latest_time = max(r.updated_at for r in current_group)
                    groups.append({
                        'timestamp': latest_time,
                        'records': current_group
                    })
                
                # Start new group
                current_group = [record]
                current_group_start = record_time
        
        # Add the last group
        if current_group:
            latest_time = max(r.updated_at for r in current_group)
            groups.append({
                'timestamp': latest_time,
                'records': current_group
            })
        
        # ===== 3. Fetch IP Addresses and Geolocations for Each Group =====
        ip_query = IPQuery()
        geoip_query = HistoryGeoIPQuery()
        time_groups: List[IPHoppingTimeGroup] = []
        previous_hash: Optional[str] = None
        
        for group in groups:
            timestamp = group['timestamp']
            records = group['records']
            
            # Get unique IP IDs in this group
            unique_ip_ids = list(set(r.ip_id for r in records))
            
            # Fetch IP addresses using the new function
            ips_data = await ip_query.ips_by_id_list(info=info, id_list=unique_ip_ids)
            
            # Create IP location list for this group
            ip_locations: List[IPLocation] = []
            
            for ip_data in ips_data:
                ip_id = ip_data.id
                ip_address = ip_data.ip_address
                
                # Find the record for this IP to get its timestamp
                ip_record = next((r for r in records if r.ip_id == ip_id), None)
                if not ip_record:
                    continue
                
                # Fetch geolocation at that time using history_geoip_at_time
                geoip = await geoip_query.history_geoip_at_time(
                    info=info,
                    ip_id=ip_id,
                    target_datetime=ip_record.updated_at.isoformat()
                )
                
                # Parse latitude and longitude from "lat,long" format
                latitude = None
                longitude = None
                if geoip and geoip.latitude_longitude:
                    try:
                        lat_long_parts = geoip.latitude_longitude.split(',')
                        if len(lat_long_parts) == 2:
                            latitude = lat_long_parts[0].strip()
                            longitude = lat_long_parts[1].strip()
                    except Exception:
                        pass
                
                ip_locations.append(
                    IPLocation(
                        ip_address=ip_address,
                        latitude=latitude,
                        longitude=longitude
                    )
                )
            
            # Sort IP locations by IP address for consistent hashing
            ip_locations.sort(key=lambda x: x.ip_address)
            
            # ===== 4. Calculate Hash to Detect Duplicates =====
            # Create a hashable representation of this group (excluding timestamp)
            group_content = [
                {
                    'ip': loc.ip_address,
                    'lat': loc.latitude,
                    'lon': loc.longitude
                }
                for loc in ip_locations
            ]
            group_json = json.dumps(group_content, sort_keys=True)
            current_hash = hashlib.md5(group_json.encode()).hexdigest()
            
            # Only add if different from previous group
            if current_hash != previous_hash:
                time_groups.append(
                    IPHoppingTimeGroup(
                        timestamp=timestamp.isoformat(),
                        ips=ip_locations
                    )
                )
                previous_hash = current_hash
        
        # ===== Return Result =====
        return IPHoppingVisualization(
            domain_id=domain_id,
            time_groups=time_groups
        )
