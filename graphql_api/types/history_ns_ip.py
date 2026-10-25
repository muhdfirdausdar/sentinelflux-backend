"""
History Nameserver IP GraphQL Type
Type definition for HistoryNameserverIP table
"""
from datetime import datetime
import strawberry


@strawberry.type
class HistoryNameserverIP:
    """Historical nameserver-IP connection record"""
    ip_id: int
    nameserver_id: int
    ttl: int
    updated_at: datetime
