from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class FastFluxAnalysisBase(BaseModel):
    domain_id: int
    flux_type: str
    detected_on: datetime

    model_config = {
        "from_attributes": True
    }


class FastFluxAnalysisOut(FastFluxAnalysisBase):
    id: int

    model_config = {
        "from_attributes": True
    }


class FastFluxAnalysisColumn(str, Enum):
    ID = "id"
    DOMAIN_ID = "domain_id"
    FLUX_TYPE = "flux_type"
    DETECTED_ON = "detected_on"

    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    @property
    def aliases(self):
        """Alternative string representation for this column[only use this for url pagination params mapping]"""
        alias_mapping = {
            "domain_id": "dom_id",
            "flux_type": "flux_type",
            "detected_on": "ff_detected"
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
        return "fast_flux_analysis"

    @classmethod
    def operations_col(cls, col_name: str):
        """Get operational column if the given name matches"""
        operational_cols = []  # Add operational columns here if needed
        if col_name in operational_cols:
            return col_name
        return None
