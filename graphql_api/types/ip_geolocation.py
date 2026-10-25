"""
IP Geolocation GraphQL Type
Type definition for IPGeolocation table
"""
from datetime import datetime
import strawberry


@strawberry.type
class IPGeolocation:
    """IP geolocation information"""
    id: int
    ip_id: int
    continent: str
    country: str
    latitude_longitude: str
    asn: int
    aso: str
    first_seen: datetime
    last_seen: datetime
