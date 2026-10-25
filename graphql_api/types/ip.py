"""
IP GraphQL Type
Type definition for IPs table
"""
from datetime import datetime
from typing import List
import strawberry


@strawberry.type
class IP:
    """IP address with all information"""
    id: int
    ip_address: str
    first_seen: datetime
    last_seen: datetime


@strawberry.type
class IPResponse:
    """IP query results"""
    items: List[IP]
    total_count: int
