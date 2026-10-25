"""
Domain Filter Types
Filter inputs specific to domain queries
"""
from typing import Optional, List
import strawberry
from .base import StringFilter, IntFilter, DateFilter
from ..enums import DomainStatusEnum, FastFluxTypeEnum, SortOrder


@strawberry.input
class DomainFilterInput:
    """Advanced domain filtering options"""
    # String filters
    domain_name: Optional[StringFilter] = None
    domain_analysis_type: Optional[StringFilter] = None
    remarks: Optional[StringFilter] = None
    
    # Enum filters
    status: Optional[DomainStatusEnum] = None
    status_in: Optional[List[DomainStatusEnum]] = None  # Multiple statuses
    
    # Number filters
    id: Optional[IntFilter] = None
    source_id: Optional[IntFilter] = None
    total_analysis_done: Optional[IntFilter] = None
    
    # Date filters
    first_seen: Optional[DateFilter] = None
    last_seen: Optional[DateFilter] = None
    last_ff_analysis: Optional[DateFilter] = None
    
    # Boolean filters
    wait_to_ff_analysis: Optional[bool] = None
    is_unrated: Optional[bool] = None
    
    # Relationship filters
    has_source: Optional[bool] = None  # Has source_id or not
    has_ff_analysis: Optional[bool] = None  # Has any FF analysis
    flux_type: Optional[FastFluxTypeEnum] = None  # Filter by specific flux type
    
    # Search across multiple fields
    search: Optional[str] = None  # Search in domain_name, remarks, analysis_type


@strawberry.input
class DomainSortInput:
    """Sorting options for domains"""
    field: str  # 'id', 'domain_name', 'first_seen', 'last_seen', 'total_analysis_done'
    order: SortOrder = SortOrder.DESC
