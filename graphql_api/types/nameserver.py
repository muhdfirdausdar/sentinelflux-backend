"""
Nameserver GraphQL Type
Type definition for Nameserver table
"""
from typing import List, Optional
import strawberry


@strawberry.type
class Nameserver:
    """Nameserver with all information"""
    id: int
    nameserver: str
    remarks: Optional[str]


@strawberry.type
class NameserverResponse:
    """Nameserver query results"""
    items: List[Nameserver]
    total_count: int
