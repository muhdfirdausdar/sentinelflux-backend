"""
Source Query Resolvers
All query operations for Sources table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..types.source import Source

# Import model
from models.sources import Sources as SourcesModel


@strawberry.type
class SourceQuery:
    """Query operations for Sources table"""
    
    @strawberry.field
    async def sources(
        self,
        info: Info,
        limit: int = 50,
        offset: int = 0
    ) -> List[Source]:
        """Get all sources"""
        db: AsyncSession = info.context["db"]
        
        query = select(SourcesModel).order_by(desc(SourcesModel.id))
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        sources = result.scalars().all()
        
        return [
            Source(id=s.id, name=s.name)
            for s in sources
        ]
    
    @strawberry.field
    async def source_by_id(
        self,
        info: Info,
        id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Optional[Source]:
        """Get a specific source by ID or name"""
        db: AsyncSession = info.context["db"]
        
        if id:
            query = select(SourcesModel).where(SourcesModel.id == id)
        elif name:
            query = select(SourcesModel).where(SourcesModel.name == name)
        else:
            return None
        
        result = await db.execute(query)
        source = result.scalar_one_or_none()
        
        if not source:
            return None
        
        return Source(id=source.id, name=source.name)
    
    @strawberry.field
    async def sources_count(self, info: Info) -> int:
        """Get total number of sources"""
        db: AsyncSession = info.context["db"]
        
        query = select(func.count(SourcesModel.id))
        result = await db.execute(query)
        return result.scalar() or 0
