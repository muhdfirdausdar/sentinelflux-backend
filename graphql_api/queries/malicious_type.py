"""
Malicious Type Query Resolvers
All query operations for MaliciousTypes table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..types.malicious_type import MaliciousType

# Import model
from models.malicious_types import MaliciousType as MaliciousTypeModel


@strawberry.type
class MaliciousTypeQuery:
    """Query operations for MaliciousTypes table"""
    
    @strawberry.field
    async def malicious_types(
        self,
        info: Info,
        limit: int = 50,
        offset: int = 0
    ) -> List[MaliciousType]:
        """
        Get all malicious types
        
        GraphQL Query Examples:
        
        # Get all malicious types
        {
          maliciousTypes {
            id
            name
          }
        }
        
        # Get with pagination
        {
          maliciousTypes(limit: 10, offset: 0) {
            id
            name
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(MaliciousTypeModel).order_by(MaliciousTypeModel.name).offset(offset).limit(limit)
        result = await db.execute(query)
        types = result.scalars().all()
        
        return [
            MaliciousType(id=t.id, name=t.name)
            for t in types
        ]
    
    @strawberry.field
    async def malicious_type_by_id(
        self,
        info: Info,
        id: int
    ) -> Optional[MaliciousType]:
        """
        Get a specific malicious type by ID
        
        GraphQL Query Examples:
        
        # Get malicious type by ID
        {
          maliciousTypeById(id: 1) {
            id
            name
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(MaliciousTypeModel).where(MaliciousTypeModel.id == id)
        result = await db.execute(query)
        mal_type = result.scalar_one_or_none()
        
        if not mal_type:
            return None
        
        return MaliciousType(id=mal_type.id, name=mal_type.name)
