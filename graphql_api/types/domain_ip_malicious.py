"""
Domain IP Malicious GraphQL Type
Type definition for DomainIPMalicious table
"""
from datetime import datetime
from typing import List
import strawberry


@strawberry.type
class DomainIPMalicious:
    """Malicious domain-IP record"""
    domain_ip_id: int
    malicious_type_id: int
    malicious_name: str
    source_id: int
    source_name: str
    first_seen: datetime
    last_seen: datetime


@strawberry.type
class DomainIPMaliciousStats:
    """Statistics for malicious domain-IP records"""
    total_malicious: int
    list_malicious_type: List[str]
