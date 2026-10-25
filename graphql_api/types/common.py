"""
Common GraphQL Types
Shared types used across multiple schemas
"""
from datetime import datetime
import strawberry
from ..enums import FastFluxTypeEnum


@strawberry.type
class Source:
    """Source information"""
    id: int
    name: str


@strawberry.type
class FastFluxAnalysis:
    """Fast Flux Analysis result"""
    id: int
    flux_type: FastFluxTypeEnum
    detected_on: datetime
