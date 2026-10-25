"""
History Domain Nameserver GraphQL Type
Type definition for HistoryDomainNameserver table
"""
from datetime import datetime
import strawberry


@strawberry.type
class HistoryDomainNameserver:
    """Historical domain-nameserver connection record"""
    domain_id: int
    nameserver_id: int
    ttl: int
    updated_at: datetime
