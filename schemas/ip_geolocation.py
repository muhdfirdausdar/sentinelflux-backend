# schemas/ip_geolocation.py

from typing import List
from pydantic import BaseModel
from datetime import datetime

class IPGeolocationBase(BaseModel):
    ip_id: int
    continent: str
    country: str
    latitude_longitude: str
    asn: int
    aso: str
    first_seen: datetime
    last_seen: datetime

    model_config = {
        "from_attributes": True
    }

class IPGeolocationOut(IPGeolocationBase):
    id: int

    model_config = {
        "from_attributes": True
    }


# Pydantic model for response structure
class GeoIPResponse(BaseModel):
    ip_id: int
    ip: str
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: str
    highest_ttl: int
    highest_ttl_time: datetime
    first_seen: str
    last_seen: str
    continent: str
    country: str
    latitude_longitude: str
    asn: int
    aso: str
    ipgeo_first_seen: str
    ipgeo_last_seen: str
    total_ip_to_geo_relation: int
    total_ip_to_domain_relation: int
    total_ip_to_ns_relation: int      
