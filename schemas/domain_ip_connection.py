# schemas/domain_ip_connection.py

from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional

from enum import Enum


class DomainIPConnectionBase(BaseModel):
    domain_id: int
    ip_id: int
    first_seen: datetime
    last_seen: datetime
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl: int
    highest_ttl_time: datetime

    model_config = {
        "from_attributes": True
    }

class DomainIPConnectionOut(DomainIPConnectionBase):
    id: int

    model_config = {
        "from_attributes": True
    }

class DomainIPStats(BaseModel):
    """Statistics for IP connections of a single domain"""
    id_list: Optional[List[int]] = None
    count_ips: Optional[int] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    average_ttl: Optional[float] = None
    lowest_ttl: Optional[int] = None
    lowest_ttl_time: Optional[datetime] = None
    highest_ttl: Optional[int] = None
    highest_ttl_time: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }
# Type alias for the return type
DIPGetDataReturn = Dict[int, DomainIPStats]
"""
# Some domains might have incomplete stats
response_data = {
    1: DomainIPStats(id_list=[1, 2, 3], count_ips=3),  # Minimal data
    2: DomainIPStats(
        id_list=[4, 5, 6, 7],
        count_ips=4,
        average_ttl=250.0,
        first_seen=datetime.now()
        # Other fields can be None
    )
}

return response_data  # Direct dictionary return, no wrapper needed

"""

class DomainIPConnectionColumn(str, Enum):
    ID = "id"
    DOMAIN_ID = "domain_id"
    IP_ID = "ip_id"
    FIRST_SEEN = "first_seen"
    LAST_SEEN = "last_seen"
    TTL = "ttl"
    LOWEST_TTL = "lowest_ttl"
    LOWEST_TTL_TIME = "lowest_ttl_time"
    HIGHEST_TTL = "highest_ttl"
    HIGHEST_TTL_TIME = "highest_ttl_time"
    COUNT_IPS = "count_ips"  # Operational column for counting unique IPs
    IPS_AVERAGE_TTL = "average_ttl"  # Operational column for average TTL

    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    @property
    def aliases(self):
        """Alternative string representation for this column[only use this for url pagination params mapping]"""
        alias_mapping = {
            "domain_id": "dom_id",
            "ip_id": "domip_id",
            "first_seen": "domip_first_seen",
            "last_seen": "domip_last_seen",
            "ttl": "domip_ttl",
            "lowest_ttl": "domip_lowest_ttl",
            "lowest_ttl_time": "domip_lowest_ttl_time",
            "highest_ttl": "domip_highest_ttl",
            "highest_ttl_time": "domip_highest_ttl_time",
            "count_ips": "num_ips",
            "average_ttl": "domip_avg_ttl"
        }
        return alias_mapping.get(self.value, self.value)
    @classmethod
    def from_alias(cls, alias: str):
        """Get enum member from an alias string"""
        for member in cls:
            if alias == member.value or alias == member.aliases:
                return member
        return None

    @property
    def all_names(self):
        """Return all valid names for this column (canonical + alias)"""
        return [self.value, self.aliases] if self.aliases != self.value else [self.value]
    
    @property
    def table(self):
        return "domain_ip_connection"

    @classmethod
    def operations_col(cls, col_name: str):
        """Get operational column if the given name matches"""
        operational_cols = ["count_ips", "average_ips_ttl"]
        if col_name in operational_cols:
            return col_name
        return None





