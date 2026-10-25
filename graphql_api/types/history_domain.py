"""
History Domain GraphQL Type
Type definition for HistoryDomain table
"""
from datetime import datetime
import strawberry
from ..enums import DomainStatusEnum


@strawberry.type
class HistoryDomain:
    """Historical domain status record"""
    domain_id: int
    updated_at: datetime
    status: DomainStatusEnum
    remarks: str | None
