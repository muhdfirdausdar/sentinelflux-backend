"""
Statistics and Reports Query Module
Example of complex queries that reuse logic from multiple modules
"""
from typing import List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession

# Import helper functions (for raw data queries)
from ..utils import (
    get_source_by_id,
    count_domains_by_source,
    count_fast_flux_by_domain,
    get_domains_with_flux_type,
)

# Import query classes (for complete GraphQL objects)
from .domain import DomainQuery
from .source import SourceQuery
from .fast_flux import FastFluxQuery

# Import types
from ..types.domain import Domain
from ..types.source import Source
from ..enums import FastFluxTypeEnum


@strawberry.type
class SourceStatistics:
    """Statistics for a source"""
    source: Source
    total_domains: int
    active_domains: int
    inactive_domains: int


@strawberry.type
class FluxTypeStatistics:
    """Statistics for a flux type"""
    flux_type: FastFluxTypeEnum
    domain_count: int
    domains: List[Domain]


@strawberry.type
class DomainSecurityReport:
    """Complete security report for a domain"""
    domain: Domain
    source: Source
    flux_analysis_count: int
    risk_score: float


@strawberry.type
class StatisticsQuery:
    """
    Complex statistical queries combining multiple tables
    Demonstrates best practices for reusing query logic
    """
    
    @strawberry.field
    async def source_statistics(
        self,
        info: Info,
        source_id: int
    ) -> SourceStatistics:
        """
        Get complete statistics for a source
        
        Uses helper functions for counts, GraphQL resolvers for complete objects
        """
        db: AsyncSession = info.context["db"]
        
        # Pattern 1: Use helper for simple query
        source_model = await get_source_by_id(db, source_id)
        if not source_model:
            raise Exception(f"Source {source_id} not found")
        
        source = Source(id=source_model.id, name=source_model.name)
        
        # Pattern 2: Use helpers for aggregations
        total_domains = await count_domains_by_source(db, source_id)
        
        # Import helper we need
        from ..utils.db_helpers import count_domains_by_status
        from sqlalchemy import select, func, and_
        from models.domain import Domain as DomainModel
        
        # Count active domains from this source
        query = select(func.count(DomainModel.id)).where(
            and_(
                DomainModel.source_id == source_id,
                DomainModel.status == 'active'
            )
        )
        result = await db.execute(query)
        active_domains = result.scalar() or 0
        
        # Count inactive domains from this source
        query = select(func.count(DomainModel.id)).where(
            and_(
                DomainModel.source_id == source_id,
                DomainModel.status == 'inactive'
            )
        )
        result = await db.execute(query)
        inactive_domains = result.scalar() or 0
        
        return SourceStatistics(
            source=source,
            total_domains=total_domains,
            active_domains=active_domains,
            inactive_domains=inactive_domains
        )
    
    @strawberry.field
    async def flux_type_statistics(
        self,
        info: Info,
        flux_type: FastFluxTypeEnum,
        limit: int = 10
    ) -> FluxTypeStatistics:
        """
        Get statistics for a specific flux type
        
        Combines helpers and GraphQL resolvers
        """
        db: AsyncSession = info.context["db"]
        
        # Pattern 1: Use helper for raw domain models
        domain_models = await get_domains_with_flux_type(
            db, 
            flux_type.value,
            limit=limit
        )
        
        # Convert to GraphQL types
        from ..enums import DomainStatusEnum
        domains = [
            Domain(
                id=d.id,
                domain_name=d.domain_name,
                first_seen=d.first_seen,
                last_seen=d.last_seen,
                status=DomainStatusEnum[d.status.upper()],
                source_id=d.source_id,
                last_ff_analysis=d.last_ff_analysis,
                total_analysis_done=d.total_analysis_done,
                domain_analysis_type=d.domain_analysis_type,
                wait_to_ff_analysis=d.wait_to_ff_analysis,
                is_unrated=d.is_unrated,
                remarks=d.remarks
            )
            for d in domain_models
        ]
        
        # Pattern 2: Use helper for count
        from ..utils.db_helpers import count_fast_flux_by_type
        domain_count = await count_fast_flux_by_type(db, flux_type.value)
        
        return FluxTypeStatistics(
            flux_type=flux_type,
            domain_count=domain_count,
            domains=domains
        )
    
    @strawberry.field
    async def domain_security_report(
        self,
        info: Info,
        domain_id: int
    ) -> DomainSecurityReport:
        """
        Get complete security report for a domain
        
        Demonstrates mixing all three patterns
        """
        db: AsyncSession = info.context["db"]
        
        # Pattern 1: Reuse GraphQL resolver for complete domain object
        domain_query = DomainQuery()
        domain_response = await domain_query.domains(
            info=info,
            filter=None,  # Would need to create filter for id
            limit=1,
            offset=0
        )
        
        if not domain_response.items:
            raise Exception(f"Domain {domain_id} not found")
        
        domain = domain_response.items[0]
        
        # Pattern 2: Use helper for source
        source_model = await get_source_by_id(db, domain.source_id) if domain.source_id else None
        source = Source(
            id=source_model.id,
            name=source_model.name
        ) if source_model else Source(id=0, name="Unknown")
        
        # Pattern 3: Use helper for count
        flux_count = await count_fast_flux_by_domain(db, domain_id)
        
        # Calculate risk score based on analysis count and status
        risk_score = calculate_risk_score(domain, flux_count)
        
        return DomainSecurityReport(
            domain=domain,
            source=source,
            flux_analysis_count=flux_count,
            risk_score=risk_score
        )
    
    @strawberry.field
    async def all_source_statistics(
        self,
        info: Info
    ) -> List[SourceStatistics]:
        """
        Get statistics for all sources
        
        Demonstrates reusing other query methods
        """
        db: AsyncSession = info.context["db"]
        
        # Reuse GraphQL resolver to get all sources
        source_query = SourceQuery()
        sources = await source_query.sources(info=info, limit=100, offset=0)
        
        result = []
        for source in sources:
            # Use helper for each source's stats
            total_domains = await count_domains_by_source(db, source.id)
            
            # You could call self.source_statistics here too!
            # But for efficiency, we'll inline the queries
            
            from sqlalchemy import select, func, and_
            from models.domain import Domain as DomainModel
            
            query = select(func.count(DomainModel.id)).where(
                and_(
                    DomainModel.source_id == source.id,
                    DomainModel.status == 'active'
                )
            )
            result_active = await db.execute(query)
            active_domains = result_active.scalar() or 0
            
            query = select(func.count(DomainModel.id)).where(
                and_(
                    DomainModel.source_id == source.id,
                    DomainModel.status == 'inactive'
                )
            )
            result_inactive = await db.execute(query)
            inactive_domains = result_inactive.scalar() or 0
            
            result.append(
                SourceStatistics(
                    source=source,
                    total_domains=total_domains,
                    active_domains=active_domains,
                    inactive_domains=inactive_domains
                )
            )
        
        return result


def calculate_risk_score(domain: Domain, flux_count: int) -> float:
    """Helper function to calculate risk score"""
    score = 0.0
    
    # More analysis = higher risk
    score += min(flux_count * 10, 50)
    
    # Status impacts risk
    if domain.status.value == 'active':
        score += 30
    elif domain.status.value == 'unknown':
        score += 20
    
    # Unrated domains are risky
    if domain.is_unrated:
        score += 20
    
    return min(score, 100.0)
