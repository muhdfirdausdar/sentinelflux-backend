# schemas/sources.py

from pydantic import BaseModel
from enum import Enum

class SourceBase(BaseModel):
    name: str

    model_config = {
        "from_attributes": True  # enables conversion from ORM objects
    }

class SourceOut(SourceBase):
    id: int

    model_config = {
        "from_attributes": True
    }


class Sources(str, Enum):
    NAME = "name"

    @property
    def aliases(self):
        """Alternative string representation for this column[only use this for url pagination params mapping]"""
        alias_mapping = {
            "name": "source_name",
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
        return "sources"
    
    @classmethod
    def operations_col(cls, col_name: str):
        """Get operational column if the given name matches"""
        operational_cols = []  # No operational columns for sources
        if col_name in operational_cols:
            return col_name
        return None
