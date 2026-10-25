from enum import Enum
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .ip_geolocation import GeoIPResponse

class DomainStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class DomainBase(BaseModel):
    domain_name: str
    first_seen: datetime
    last_seen: datetime
    status: DomainStatus
    remarks: Optional[str] = None
    is_unrated: Optional[bool] = None

    model_config = {
        "from_attributes": True  # replaces `orm_mode = True`
    }

class DomainOut(DomainBase):
    id: int
    source_id: Optional[int] = None

    model_config = {
        "from_attributes": True  # required for SQLAlchemy compatibility
    }


class DomainAllInfo(BaseModel):
    domain_name: str
    first_seen: str
    last_seen: str
    source_domain: Optional[str]
    domain_id: int
    malicious_info: dict
    status: str
    remarks: Optional[str]
    total_A_Records: int
    total_NS_Records: int
    total_NS_IPs: int
    A_Records: List[GeoIPResponse]
    NS_Records: List[dict]


# Enum for domain column names with inherent properties
class DomainColumn(str, Enum):
    ID = "id"
    DOMAIN_NAME = "domain_name"
    FIRST_SEEN = "first_seen"
    LAST_SEEN = "last_seen"
    STATUS = "status"
    IS_UNRATED = "is_unrated"
    SOURCE_ID = "source_id"
    LAST_FF_ANALYSIS = "last_ff_analysis"
    TOTAL_ANALYSIS_DONE = "total_analysis_done"
    DOMAIN_ANALYSIS_TYPE = "domain_analysis_type"
    REMARKS = "remarks"
    
    # Inherent properties for each enum item
    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    @property
    def aliases(self):
        """Alternative string representation for this column[only use this for url pagination params mapping]"""
        alias_mapping = {
            "domain_name": "domain_name",
            "last_seen": "dom_last_seen",
            "first_seen": "dom_first_seen",
            "status": "dom_status",
            "source_id": "source_id",
            "last_ff_analysis": "last_ff_analysis",
            "total_analysis_done": "total_analysis_count",
            "domain_analysis_type": "dom_analysis_type",
            "remarks": "dom_remarks",
            "is_unrated": "is_unrated"
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
        return "domain"


"""
DomainColumn Enum Usage Guide:
============================

This enum provides flexible column name handling with aliases and metadata.

BASIC USAGE:
-----------
from models.domain import DomainColumn

# Standard usage
column = DomainColumn.DOMAIN_NAME
print(column.value)  # "domain_name"

# Using aliases
column = DomainColumn.from_alias("domain_name")  # Same as DOMAIN_NAME
column = DomainColumn.from_alias("dom_last_seen")  # Same as LAST_SEEN

ALIAS SUPPORT:
-------------
Each enum item supports one alternative string representation:

DomainColumn.DOMAIN_NAME alias: "domain_name"
DomainColumn.LAST_SEEN alias: "dom_last_seen"  
DomainColumn.STATUS alias: "dom_status"

Example:
    DomainColumn.from_alias("dom_last_seen")  # Returns DomainColumn.LAST_SEEN
    DomainColumn.from_alias("dom_status")     # Returns DomainColumn.STATUS

PROPERTIES:
----------
Each enum item has inherent properties:

- .table: Always returns "domain"
- .aliases: Single alternative name
- .all_names: Canonical name + alias (if different)

Example:
    col = DomainColumn.DOMAIN_NAME
    print(col.table)      # "domain"
    print(col.aliases)    # "domain_name"
    print(col.all_names)  # ["domain_name"]


"""