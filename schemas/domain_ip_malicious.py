# schemas/domain_ip_malicious.py

from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DomainIPMaliciousBase(BaseModel):
    domain_ip_id: int
    malicious_type_id: int
    source_id: int
    first_seen: datetime
    last_seen: datetime

    model_config = {
        "from_attributes": True  # enables conversion from ORM objects
    }

class DomainIPMaliciousOut(DomainIPMaliciousBase):
    # No id field - using composite PK
    
    model_config = {
        "from_attributes": True
    }


class DomIPMaliciousColumn(str, Enum):
    DOMAIN_IP_ID = "domain_ip_id"
    MALICIOUS_TYPE_ID = "malicious_type_id"
    SOURCE_ID = "source_id"
    FIRST_SEEN = "first_seen"
    LAST_SEEN = "last_seen"
    IS_MALICIOUS = "is_malicious"

    @property
    def aliases(self):
        """Alternative string representation for this column[only use this for url pagination params mapping]"""
        alias_mapping = {
            "domain_ip_id": "domip_id",
            "malicious_type_id": "mal_type_id",
            "source_id": "src_id",
            "first_seen": "domip_mal_first_seen",
            "last_seen": "domip_mal_last_seen",
            "is_malicious": "is_malicious"
        }
        return alias_mapping.get(self.value, self.value)

    @classmethod
    def from_alias(cls, alias: str):
        """Get enum member from an alias"""
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
        return "domain_ip_malicious"
    
    @classmethod
    def operations_col(cls, col_name: str):
        """Get operational column if the given name matches"""
        operational_cols = ["is_malicious"]
        if col_name in operational_cols:
            return col_name
        return None
