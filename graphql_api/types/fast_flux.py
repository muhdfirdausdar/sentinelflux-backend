"""
Fast Flux Analysis GraphQL Type
Type definition for FastFluxAnalysis table
"""
from datetime import datetime
import strawberry
from ..enums import FastFluxTypeEnum


@strawberry.type
class FastFluxAnalysis:
    """Fast Flux Analysis result"""
    id: int
    domain_id: int
    flux_type: FastFluxTypeEnum
    a_record_change_frequency: int
    ns_record_change_frequency: int
    detected_on: datetime
    # details field (JSONB) can be added if needed
