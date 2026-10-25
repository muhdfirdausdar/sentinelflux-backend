"""
Domain GraphQL Types
Type definitions specific to Domain table
"""
from datetime import datetime
from typing import List, Optional
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from ..enums import DomainStatusEnum, FastFluxTypeEnum
from .source import Source
from .fast_flux import FastFluxAnalysis

# Import models
from models.sources import Sources as SourcesModel
from models.fast_flux_analysis import FastFluxAnalysis as FastFluxAnalysisModel


@strawberry.type
class Domain:
    """Domain with all its information and relationships"""
    id: int
    domain_name: str
    first_seen: datetime
    last_seen: datetime
    status: DomainStatusEnum
    source_id: Optional[int]
    last_ff_analysis: Optional[datetime]
    total_analysis_done: int
    domain_analysis_type: Optional[str]
    wait_to_ff_analysis: bool
    is_unrated: bool
    remarks: Optional[str]
    
    # Lazy-loaded relationships
    @strawberry.field
    async def source(self, info: Info) -> Optional[Source]:
        """Get the source that reported this domain"""
        db: AsyncSession = info.context["db"]
        
        if not self.source_id:
            return None
        
        query = select(SourcesModel).where(SourcesModel.id == self.source_id)
        result = await db.execute(query)
        source = result.scalar_one_or_none()
        
        if source:
            return Source(id=source.id, name=source.name)
        return None
    
    @strawberry.field
    async def fast_flux_analysis(
        self, 
        info: Info,
        flux_type: Optional[FastFluxTypeEnum] = None,
        limit: Optional[int] = None
    ) -> List[FastFluxAnalysis]:
        """Get fast flux analysis results for this domain"""
        db: AsyncSession = info.context["db"]
        
        query = select(FastFluxAnalysisModel).where(
            FastFluxAnalysisModel.domain_id == self.id
        )
        
        if flux_type:
            query = query.where(FastFluxAnalysisModel.flux_type == flux_type.value)
        
        query = query.order_by(desc(FastFluxAnalysisModel.detected_on))
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        analysis = result.scalars().all()
        
        return [
            FastFluxAnalysis(
                id=a.id,
                domain_id=a.domain_id,
                flux_type=FastFluxTypeEnum[a.flux_type.upper()],
                a_record_change_frequency=a.a_record_change_frequency,
                ns_record_change_frequency=a.ns_record_change_frequency,
                detected_on=a.detected_on
            )
            for a in analysis
        ]


@strawberry.type
class DomainResponse:
    """Domain query results"""
    items: List[Domain]
    total_count: int
