# schemas/domain_nameserver.py

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class DomainNameserverBase(BaseModel):
    domain_id: Optional[int]
    nameserver_id: Optional[int]
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl: int
    highest_ttl_time: datetime

    model_config = {
        "from_attributes": True
    }

class DomainNameserverOut(DomainNameserverBase):
    id: int
    first_seen: datetime
    last_seen: datetime

    model_config = {
        "from_attributes": True
    }

class DomainNSStats(BaseModel):
    """Statistics for NS connections of a single domain"""
    id_list: Optional[List[int]] = None
    count_ns: Optional[int] = None
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
DNSGetDataReturn = Dict[int, DomainNSStats]

"""
# Some domains might have incomplete stats
response_data = {
    1: DomainNSStats(id_list=[1, 2, 3], count_ns=3),  # Minimal data
    2: DomainNSStats(
        id_list=[4, 5, 6, 7],
        count_ns=4,
        average_ttl=250.0,
        first_seen=datetime.now()
        # Other fields can be None
    )
}

return response_data  # Direct dictionary return, no wrapper needed

"""


class DomainNameserverColumn(str, Enum):
    ID = "id"
    DOMAIN_ID = "domain_id"
    NAMESERVER_ID = "nameserver_id"
    FIRST_SEEN = "first_seen"
    LAST_SEEN = "last_seen"
    TTL = "ttl"
    LOWEST_TTL = "lowest_ttl"
    LOWEST_TTL_TIME = "lowest_ttl_time"
    HIGHEST_TTL = "highest_ttl"
    HIGHEST_TTL_TIME = "highest_ttl_time"
    NS_AVERAGE_TTL = "ns_average_ttl"  # Operational column for average TTL
    COUNT_NS = "count_ns"  # Operational column for counting unique NS


    # Inherent properties for each enum item
    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj
    
    @property
    def aliases(self):
        """Alternative string representation for this column[only use this for url pagination params mapping]"""
        alias_mapping = {
            "domain_id": "dom_id",
            "nameserver_id": "ns_id",
            "first_seen": "domns_first_seen",
            "last_seen": "domns_last_seen",
            "ttl": "domns_ttl",
            "lowest_ttl": "domns_lowest_ttl",
            "lowest_ttl_time": "domns_lowest_ttl_time",
            "highest_ttl": "domns_highest_ttl",
            "highest_ttl_time": "domns_highest_ttl_time",
            "ns_average_ttl": "domns_avg_ttl",
            "count_ns": "num_ns"
        }
        return alias_mapping.get(self.value, self.value)

    @classmethod
    def from_alias(cls, alias: str):
        """Resolve an alias to the canonical DomainColumn enum item"""
        # First check if it's already a canonical value
        for member in cls:
            if member.value == alias:
                return member
        
        # Then check aliases
        for member in cls:
            if alias == member.aliases:
                return member
        
        # Not found
        return None

    @property
    def all_names(self):
        """Return all valid names for this column (canonical + alias)"""
        return [self.value, self.aliases] if self.aliases != self.value else [self.value]

    @property
    def table(self):
        """The table this column belongs to"""
        return "domain_nameserver"

    @classmethod
    def operations_col(cls, col_name: str):
        """Get operational column if the given name matches"""
        operational_cols = ["count_ns", "ns_average_ttl"]
        if col_name in operational_cols:
            return col_name
        return None

