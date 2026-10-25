"""
History GeoIP GraphQL Type
Type definition for HistoryGeoIP table
"""
from datetime import datetime
import strawberry


@strawberry.type
class HistoryGeoIP:
    """Historical IP geolocation record"""
    ip_id: int
    continent: str
    country: str
    latitude_longitude: str
    asn: int
    aso: str
    updated_at: datetime
