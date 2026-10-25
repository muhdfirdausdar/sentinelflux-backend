"""
Nameserver Query Resolvers
All query operations for Nameserver table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..types.nameserver import Nameserver, NameserverResponse

# Import model
from models.nameserver import Nameserver as NameserverModel


@strawberry.type
class NameserverQuery:
    """Query operations for Nameserver table"""
    
    @strawberry.field
    async def nameservers(
        self,
        info: Info,
        nameserver: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> NameserverResponse:
        """
        Get nameservers with optional filtering
        
        GraphQL Query Examples:
        
        # Get all nameservers
        {
          nameservers(limit: 10) {
            items {
              id
              nameserver
              remarks
            }
            totalCount
          }
        }
        
        # Get specific nameserver
        {
          nameservers(nameserver: "ns1.example.com") {
            items {
              id
              nameserver
              domainNameservers {
                domainId
              }
            }
          }
        }
        
        # Search nameservers
        {
          nameservers(search: "google", limit: 10) {
            items {
              nameserver
              nameserverIps {
                ipId
              }
            }
            totalCount
          }
        }
        
        # Get nameservers with relationships
        {
          nameservers(limit: 5) {
            items {
              nameserver
              domainNameservers {
                domainId
              }
              nameserverIps {
                ipId
              }
            }
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(NameserverModel)
        
        # Apply filters
        if nameserver:
            query = query.where(NameserverModel.nameserver == nameserver)
        elif search:
            query = query.where(NameserverModel.nameserver.ilike(f"%{search}%"))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(NameserverModel.id)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        nameservers = result.scalars().all()
        
        return NameserverResponse(
            items=[
                Nameserver(
                    id=ns.id,
                    nameserver=ns.nameserver,
                    remarks=ns.remarks
                )
                for ns in nameservers
            ],
            total_count=total_count
        )
    
    @strawberry.field
    async def nameserver_by_id(
        self,
        info: Info,
        id_list: List[int]
    ) -> List[Nameserver]:
        """
        Get nameservers by list of IDs (returns in same order as input)
        
        GraphQL Query Examples:
        
        # Get multiple nameservers by IDs
        {
          nameserverById(idList: [1, 5, 3]) {
            id
            nameserver
            remarks
          }
        }
        
        # Get nameservers with IPs
        {
          nameserverById(idList: [1, 2, 3]) {
            id
            nameserver
            nameserverIps {
              ipId
              ttl
            }
          }
        }
        
        # Note: Results are returned in the same order as the input idList
        # If an ID is not found, it will be skipped in the results
        """
        db: AsyncSession = info.context["db"]
        
        if not id_list:
            return []
        
        # Fetch all nameservers in the id_list
        query = select(NameserverModel).where(NameserverModel.id.in_(id_list))
        result = await db.execute(query)
        nameservers = result.scalars().all()
        
        # Create a dictionary for quick lookup
        ns_dict = {ns.id: ns for ns in nameservers}
        
        # Return nameservers in the same order as id_list
        ordered_results = []
        for ns_id in id_list:
            if ns_id in ns_dict:
                ns = ns_dict[ns_id]
                ordered_results.append(
                    Nameserver(
                        id=ns.id,
                        nameserver=ns.nameserver,
                        remarks=ns.remarks
                    )
                )
        
        return ordered_results
