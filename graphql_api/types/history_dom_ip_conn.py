"""
History Domain IP Connection GraphQL Type
Type definition for HistoryDomainIPConnection table
"""
from datetime import datetime
import strawberry


@strawberry.type
class HistoryDomainIPConnection:
    """Historical domain-IP connection record"""
    domain_id: int
    ip_id: int
    ttl: int
    updated_at: datetime
