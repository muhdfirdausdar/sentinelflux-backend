"""
IP Query Resolvers
All query operations for IPs table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from ..types.ip import IP, IPResponse

# Import model
from models.ips import IP as IPModel


@strawberry.type
class IPQuery:
    """Query operations for IPs table"""
    
    @strawberry.field
    async def ips(
        self,
        info: Info,
        ip_address: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> IPResponse:
        """
        Get IPs with optional filtering
        
        GraphQL Query Examples:
        
        # Get all IPs
        {
          ips(limit: 10) {
            items {
              id
              ipAddress
              firstSeen
              lastSeen
            }
            totalCount
          }
        }
        
        # Search for specific IP
        {
          ips(ipAddress: "192.168.1.1") {
            items {
              id
              ipAddress
              geolocations {
                country
                asn
              }
            }
          }
        }
        
        # Search IPs (partial match)
        {
          ips(search: "192.168", limit: 10) {
            items {
              ipAddress
              domainConnections {
                domainId
              }
            }
            totalCount
          }
        }
        
        # Get IPs with relationships
        {
          ips(limit: 5) {
            items {
              ipAddress
              geolocations {
                country
                continent
              }
              domainConnections {
                domainId
              }
            }
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(IPModel)
        
        # Apply filters
        if ip_address:
            query = query.where(IPModel.ip_address == ip_address)
        elif search:
            query = query.where(IPModel.ip_address.cast(str).like(f"%{search}%"))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(IPModel.id)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        ips = result.scalars().all()
        
        return IPResponse(
            items=[
                IP(
                    id=ip.id,
                    ip_address=str(ip.ip_address),
                    first_seen=ip.first_seen,
                    last_seen=ip.last_seen
                )
                for ip in ips
            ],
            total_count=total_count
        )
    
    @strawberry.field
    async def ip_by_id(
        self,
        info: Info,
        id: int
    ) -> Optional[IP]:
        """
        Get a specific IP by ID
        
        GraphQL Query Examples:
        
        # Get IP by ID
        {
          ipById(id: 1) {
            id
            ipAddress
            firstSeen
            lastSeen
          }
        }
        
        # Get IP with geolocations
        {
          ipById(id: 1) {
            ipAddress
            geolocations {
              country
              continent
              asn
              aso
            }
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(IPModel).where(IPModel.id == id)
        result = await db.execute(query)
        ip = result.scalar_one_or_none()
        
        if not ip:
            return None
        
        return IP(
            id=ip.id,
            ip_address=str(ip.ip_address),
            first_seen=ip.first_seen,
            last_seen=ip.last_seen
        )
    
    @strawberry.field
    async def ips_by_id_list(
        self,
        info: Info,
        id_list: List[int]
    ) -> List[IP]:
        """
        Get multiple IPs by list of IDs
        
        GraphQL Query Examples:
        
        # Get multiple IPs by IDs
        {
          ipsByIdList(idList: [1, 5, 3, 10]) {
            id
            ipAddress
            firstSeen
            lastSeen
          }
        }
        
        # Get IPs with geolocations
        {
          ipsByIdList(idList: [1, 2, 3]) {
            id
            ipAddress
            geolocations {
              country
              asn
              aso
            }
          }
        }
        
        Returns:
        - List of IPs in the same order as the input idList
        - Skips IDs that are not found
        """
        db: AsyncSession = info.context["db"]
        
        if not id_list:
            return []
        
        # Fetch all IPs in the id_list
        query = select(IPModel).where(IPModel.id.in_(id_list))
        result = await db.execute(query)
        ips = result.scalars().all()
        
        # Create a dictionary for quick lookup
        ip_dict = {ip.id: ip for ip in ips}
        
        # Return IPs in the same order as id_list
        ordered_results = []
        for ip_id in id_list:
            if ip_id in ip_dict:
                ip = ip_dict[ip_id]
                ordered_results.append(
                    IP(
                        id=ip.id,
                        ip_address=str(ip.ip_address),
                        first_seen=ip.first_seen,
                        last_seen=ip.last_seen
                    )
                )
        
        return ordered_results
