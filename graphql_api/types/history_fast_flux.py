"""
History Fast Flux Analysis GraphQL Type
Type definition for HistoryFastFluxAnalysis table
"""
from datetime import datetime
import strawberry
from ..enums import FastFluxTypeEnum


@strawberry.type
class HistoryFastFluxAnalysis:
    """Historical fast flux analysis record"""
    domain_id: int
    flux_type: FastFluxTypeEnum
    details: strawberry.scalars.JSON
    a_record_change_frequency: int
    ns_record_change_frequency: int
    updated_at: datetime
