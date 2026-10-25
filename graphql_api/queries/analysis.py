"""
Example: Complex Cross-Module Query Pattern
Demonstrates how to reuse resolvers from different modules
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession

from ..types.domain import Domain
from ..types.source import Source
from ..types.fast_flux import FastFluxAnalysis

# Import the query classes (to reuse their methods)
from .domain import DomainQuery
from .source import SourceQuery
from .fast_flux import FastFluxQuery


@strawberry.type
class AnalysisQuery:
    """
    Complex queries that combine data from multiple tables
    Reuses existing resolvers instead of repeating SQL queries
    """
    
    @strawberry.field
    async def domain_with_full_analysis(
        self, 
        info: Info, 
        domain_id: int
    ) -> Optional["DomainAnalysisResult"]:
        """
        Get complete domain analysis including source and fast flux data
        Reuses resolvers from DomainQuery, SourceQuery, and FastFluxQuery
        """
        # Create instances of the query classes
        domain_query = DomainQuery()
        source_query = SourceQuery()
        fast_flux_query = FastFluxQuery()
        
        # ✅ GOOD: Reuse existing domain query logic
        domain_response = await domain_query.domains(
            info=info,
            filter=strawberry.UNSET,  # or create filter object
            sort=None,
            limit=1,
            offset=0
        )
        
        if not domain_response.items:
            return None
        
        domain = domain_response.items[0]
        
        # ✅ GOOD: Reuse source query logic
        source = None
        if domain.source_id:
            source = await source_query.source(
                info=info,
                id=domain.source_id
            )
        
        # ✅ GOOD: Reuse fast flux query logic
        analysis = await fast_flux_query.fast_flux_analysis(
            info=info,
            domain_id=domain_id,
            flux_type=None,
            limit=10,
            offset=0
        )
        
        return DomainAnalysisResult(
            domain=domain,
            source=source,
            fast_flux_analysis=analysis
        )
    
    @strawberry.field
    async def sources_with_domain_count(
        self,
        info: Info
    ) -> List["SourceWithStats"]:
        """
        Get all sources with count of domains from each
        Demonstrates aggregation across modules
        """
        db: AsyncSession = info.context["db"]
        source_query = SourceQuery()
        domain_query = DomainQuery()
        
        # ✅ Get all sources using existing resolver
        sources = await source_query.sources(info=info, limit=100, offset=0)
        
        result = []
        for source in sources:
            # ✅ Count domains from this source
            domains_response = await domain_query.domains(
                info=info,
                filter=None,  # Would need to create filter for source_id
                limit=0,  # Just need count
                offset=0
            )
            
            result.append(
                SourceWithStats(
                    source=source,
                    domain_count=domains_response.total_count
                )
            )
        
        return result


# Supporting types for complex queries
@strawberry.type
class DomainAnalysisResult:
    """Complete analysis result combining multiple tables"""
    domain: Domain
    source: Optional[Source]
    fast_flux_analysis: List[FastFluxAnalysis]


@strawberry.type
class SourceWithStats:
    """Source with aggregated statistics"""
    source: Source
    domain_count: int
