"""
Nameserver IP GraphQL Type
Type definition for NameserverIP table
"""
from datetime import datetime
from typing import List, Optional
import strawberry


@strawberry.type
class NameserverIP:
    """Nameserver-IP connection record"""
    id: int
    nameserver_id: int
    ip_id: int
    ip_address: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl: int
    highest_ttl_time: datetime
    country: Optional[str] = None
    asn_aso: Optional[str] = None


@strawberry.type
class NameserverIPCount:
    """Count and list of nameservers for a specific IP"""
    total_ns_id: int
    list_ns_id: List[int]


@strawberry.type
class IPCountByNameserver:
    """Count and list of IPs for a specific nameserver"""
    count_ips: int
    list_ips: List[int]
