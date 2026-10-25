"""
Domain Mutation Resolvers
All mutation operations for Domain table
"""
from datetime import datetime
from typing import Optional
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..types import Domain
from ..enums import DomainStatusEnum

# Import models
from models.domain import Domain as DomainModel


@strawberry.type
class DomainMutation:
    """Mutation operations for Domain table"""
    
    @strawberry.mutation
    async def update_domain_status(
        self,
        info: Info,
        id: int,
        status: DomainStatusEnum
    ) -> Optional[Domain]:
        """Update domain status"""
        db: AsyncSession = info.context["db"]
        
        query = select(DomainModel).where(DomainModel.id == id)
        result = await db.execute(query)
        domain = result.scalar_one_or_none()
        
        if not domain:
            return None
        
        domain.status = status.value
        domain.last_seen = datetime.utcnow()
        await db.commit()
        await db.refresh(domain)
        
        return Domain(
            id=domain.id,
            domain_name=domain.domain_name,
            first_seen=domain.first_seen,
            last_seen=domain.last_seen,
            status=DomainStatusEnum[domain.status.upper()],
            source_id=domain.source_id,
            last_ff_analysis=domain.last_ff_analysis,
            total_analysis_done=domain.total_analysis_done,
            domain_analysis_type=domain.domain_analysis_type,
            wait_to_ff_analysis=domain.wait_to_ff_analysis,
            is_unrated=domain.is_unrated,
            remarks=domain.remarks
        )
    
    @strawberry.mutation
    async def update_domain_remarks(
        self,
        info: Info,
        id: int,
        remarks: str
    ) -> Optional[Domain]:
        """Update domain remarks"""
        db: AsyncSession = info.context["db"]
        
        query = select(DomainModel).where(DomainModel.id == id)
        result = await db.execute(query)
        domain = result.scalar_one_or_none()
        
        if not domain:
            return None
        
        domain.remarks = remarks[:500]  # Enforce limit
        await db.commit()
        await db.refresh(domain)
        
        return Domain(
            id=domain.id,
            domain_name=domain.domain_name,
            first_seen=domain.first_seen,
            last_seen=domain.last_seen,
            status=DomainStatusEnum[domain.status.upper()],
            source_id=domain.source_id,
            last_ff_analysis=domain.last_ff_analysis,
            total_analysis_done=domain.total_analysis_done,
            domain_analysis_type=domain.domain_analysis_type,
            wait_to_ff_analysis=domain.wait_to_ff_analysis,
            is_unrated=domain.is_unrated,
            remarks=domain.remarks
        )
