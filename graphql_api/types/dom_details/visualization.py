"""
Visualization Type for Domain Details
Type definitions for IP hopping visualization
"""
import strawberry
from typing import List, Optional


@strawberry.type
class IPLocation:
    """IP address with geolocation coordinates"""
    ip_address: str
    latitude: Optional[str]
    longitude: Optional[str]


@strawberry.type
class IPHoppingTimeGroup:
    """Group of IPs at a specific point in time"""
    timestamp: str  # Latest datetime of this group
    ips: List[IPLocation]


@strawberry.type
class IPHoppingVisualization:
    """Container for IP hopping visualization data"""
    domain_id: int
    time_groups: List[IPHoppingTimeGroup]
