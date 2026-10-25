"""
Fast Flux Analysis Query Resolvers
All query operations for FastFluxAnalysis table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ..types.fast_flux import FastFluxAnalysis
from ..enums import FastFluxTypeEnum

# Import model
from models.fast_flux_analysis import FastFluxAnalysis as FastFluxAnalysisModel


@strawberry.type
class FastFluxQuery:
    """Query operations for FastFluxAnalysis table"""
    
    @strawberry.field
    async def fast_flux_analysis(
        self,
        info: Info,
        domain_id: Optional[int] = None,
        flux_type: Optional[FastFluxTypeEnum] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[FastFluxAnalysis]:
        """
        Get multiple fast flux analysis with optional filtering
        
        GraphQL Query Examples:
        
        # Get all analysis with limit
        query {
          fastFluxAnalysis(limit: 10) {
            id
            domainId
            fluxType
            aRecordChangeFrequency
            nsRecordChangeFrequency
            detectedOn
          }
        }
        
        # Get by domain ID
        query {
          fastFluxAnalysis(domainId: 5, limit: 10) {
            id
            domainId
            fluxType
            aRecordChangeFrequency
            nsRecordChangeFrequency
            detectedOn
          }
        }
        
        # Get by flux type
        query {
          fastFluxAnalysis(fluxType: SINGLE, limit: 10) {
            id
            domainId
            fluxType
            aRecordChangeFrequency
            detectedOn
          }
        }
        
        # Get by domain and type with pagination
        query {
          fastFluxAnalysis(domainId: 5, fluxType: DOUBLE, limit: 20, offset: 0) {
            id
            domainId
            fluxType
            aRecordChangeFrequency
            nsRecordChangeFrequency
            detectedOn
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(FastFluxAnalysisModel)
        
        conditions = []
        if domain_id:
            conditions.append(FastFluxAnalysisModel.domain_id == domain_id)
        if flux_type:
            conditions.append(FastFluxAnalysisModel.flux_type == flux_type.value)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(FastFluxAnalysisModel.detected_on))
        query = query.offset(offset).limit(limit)
        
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
    
    @strawberry.field
    async def fast_flux_analysis_by_id(
        self,
        info: Info,
        id: int
    ) -> Optional[FastFluxAnalysis]:
        """
        Get a specific fast flux analysis by ID
        
        GraphQL Query Example:
        
        # Get specific analysis by ID
        query {
          fastFluxAnalysisById(id: 123) {
            id
            domainId
            fluxType
            aRecordChangeFrequency
            nsRecordChangeFrequency
            detectedOn
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(FastFluxAnalysisModel).where(FastFluxAnalysisModel.id == id)
        result = await db.execute(query)
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            return None
        
        return FastFluxAnalysis(
            id=analysis.id,
            domain_id=analysis.domain_id,
            flux_type=FastFluxTypeEnum[analysis.flux_type.upper()],
            a_record_change_frequency=analysis.a_record_change_frequency,
            ns_record_change_frequency=analysis.ns_record_change_frequency,
            detected_on=analysis.detected_on
        )
