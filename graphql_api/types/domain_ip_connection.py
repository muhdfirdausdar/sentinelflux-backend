"""
Domain IP Connection GraphQL Type
Type definition for DomainIPConnection table
"""
from datetime import datetime
from typing import List, Optional
import strawberry


@strawberry.type
class DomainIPConnection:
    """Domain-IP connection record"""
    id: int
    domain_id: int
    ip_id: int
    ip_address: Optional[str]  # IP address string
    first_seen: datetime
    last_seen: datetime
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl: int
    highest_ttl_time: datetime
    malicious_types: List[str]  # List of malicious type names
    malicious_sources: List[str]  # List of source names that reported malicious activity
    country: Optional[str]  # Country from IP geolocation
    asn_aso: Optional[str]  # ASN and ASO combined (e.g., "AS15169 Google LLC")
    latitude_longitude: Optional[str]  # Geographic coordinates


@strawberry.type
class DomainIPConnectionInfo:
    """Aggregated information about domain-IP connections for a specific domain"""
    domain_id: int
    total_ips: int
    first_seen: datetime
    last_seen: datetime
    latest_ttl: int
    lowest_ttl: int
    highest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl_time: datetime
    list_country: List[str]  # Distinct list of countries from all IPs


@strawberry.type
class IPReuseInfo:
    """Information about how many domains are using a specific IP"""
    ip_id: int
    total_domain_reused: int  # Number of domains using this IP (excluding the specified domain)
    list_domain: List[int]  # List of domain IDs using this IP (excluding the specified domain)
