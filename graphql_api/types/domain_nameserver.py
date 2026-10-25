"""
Domain Nameserver GraphQL Type
Type definition for DomainNameserver table
"""
from datetime import datetime
from typing import Optional, List
import strawberry


@strawberry.type
class DomainNameserver:
    """Domain-Nameserver connection record"""
    id: int
    domain_id: Optional[int]
    nameserver_id: Optional[int]
    nameserver: Optional[str] = None  # Nameserver name
    first_seen: datetime
    last_seen: datetime
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl: int
    highest_ttl_time: datetime
    countries: List[str]  # List of countries where nameserver IPs are located


@strawberry.type
class DomainNameserverInfo:
    """Aggregated information about domain-nameserver connections for a specific domain"""
    domain_id: int
    total_nameservers: int
    first_seen: datetime
    last_seen: datetime
    latest_ttl: int
    lowest_ttl: int
    highest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl_time: datetime
    list_country: List[str]  # Distinct list of countries from all nameserver IPs


@strawberry.type
class DomainNameserverCount:
    """Count and list of nameservers for a specific domain"""
    count: int
    nameserver_ids: List[int]
