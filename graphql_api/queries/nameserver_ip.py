"""
Nameserver IP Query Resolvers
All query operations for NameserverIP table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from ..types.nameserver_ip import NameserverIP, NameserverIPCount, IPCountByNameserver

# Import models
from models.nameserver_ip import NameserverIP as NameserverIPModel
from models.ip_geolocation import IPGeolocation as IPGeolocationModel
from models.ips import IP as IPModel


@strawberry.type
class NameserverIPQuery:
    """Query operations for NameserverIP table"""
    
    @strawberry.field
    async def nameserver_ips(
        self,
        info: Info,
        nameserver_id: Optional[int] = None,
        ip_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[NameserverIP]:
        """
        Get nameserver-IP connections with optional filtering
        
        GraphQL Query Examples:
        
        # Get all connections
        {
          nameserverIps(limit: 10) {
            id
            nameserverId
            ipId
            ttl
            firstSeen
            lastSeen
          }
        }
        
        # Get IPs for specific nameserver
        {
          nameserverIps(nameserverId: 5) {
            ipId
            ttl
            firstSeen
          }
        }
        
        # Get nameservers using specific IP
        {
          nameserverIps(ipId: 10) {
            nameserverId
            ttl
            lastSeen
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(NameserverIPModel)
        
        # Apply filters
        conditions = []
        if nameserver_id:
            conditions.append(NameserverIPModel.nameserver_id == nameserver_id)
        if ip_id:
            conditions.append(NameserverIPModel.ip_id == ip_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(NameserverIPModel.last_seen)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        conns = result.scalars().all()
        
        # Build response with geolocation info for each connection
        response = []
        for c in conns:
            # Fetch IP address
            ip_query = select(IPModel.ip_address).where(IPModel.id == c.ip_id)
            ip_result = await db.execute(ip_query)
            ip_addr_value = ip_result.scalar_one_or_none()
            ip_address = str(ip_addr_value) if ip_addr_value else None
            
            # Fetch geolocation data for this IP
            geo_query = select(
                IPGeolocationModel.country,
                IPGeolocationModel.asn,
                IPGeolocationModel.aso
            ).where(
                IPGeolocationModel.ip_id == c.ip_id
            ).order_by(desc(IPGeolocationModel.last_seen)).limit(1)
            
            geo_result = await db.execute(geo_query)
            geo_data = geo_result.one_or_none()
            
            country = None
            asn_aso = None
            if geo_data:
                country = geo_data[0]
                asn_aso = f"AS{geo_data[1]} {geo_data[2]}"  # Format: "AS15169 Google LLC"
            
            response.append(
                NameserverIP(
                    id=c.id,
                    nameserver_id=c.nameserver_id,
                    ip_id=c.ip_id,
                    ip_address=ip_address,
                    first_seen=c.first_seen,
                    last_seen=c.last_seen,
                    ttl=c.ttl,
                    lowest_ttl=c.lowest_ttl,
                    lowest_ttl_time=c.lowest_ttl_time,
                    highest_ttl=c.highest_ttl,
                    highest_ttl_time=c.highest_ttl_time,
                    country=country,
                    asn_aso=asn_aso
                )
            )
        
        return response
    
    @strawberry.field
    async def nameserver_ip_by_id(
        self,
        info: Info,
        id: int
    ) -> Optional[NameserverIP]:
        """
        Get a specific nameserver-IP connection by ID
        
        GraphQL Query Examples:
        
        # Get connection by ID
        {
          nameserverIpById(id: 1) {
            id
            nameserverId
            ipId
            ttl
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(NameserverIPModel).where(NameserverIPModel.id == id)
        result = await db.execute(query)
        conn = result.scalar_one_or_none()
        
        if not conn:
            return None
        
        return NameserverIP(
            id=conn.id,
            nameserver_id=conn.nameserver_id,
            ip_id=conn.ip_id,
            first_seen=conn.first_seen,
            last_seen=conn.last_seen,
            ttl=conn.ttl,
            lowest_ttl=conn.lowest_ttl,
            lowest_ttl_time=conn.lowest_ttl_time,
            highest_ttl=conn.highest_ttl,
            highest_ttl_time=conn.highest_ttl_time
        )
    
    @strawberry.field
    async def count_ips_for_nameservers(
        self,
        info: Info,
        nameserver_ids: List[int]
    ) -> int:
        """
        Count total number of IPs across multiple nameservers (combined count)
        
        GraphQL Query Examples:
        
        # Get total IP count for single nameserver
        {
          countIpsForNameservers(nameserverIds: [5])
        }
        
        # Get combined IP count for multiple nameservers
        {
          countIpsForNameservers(nameserverIds: [5, 10, 15, 20])
        }
        
        # Get count for all nameservers in a list
        {
          countIpsForNameservers(nameserverIds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        }
        """
        db: AsyncSession = info.context["db"]
        
        if not nameserver_ids:
            return 0
        
        # Count total IP connections for all specified nameservers
        query = select(func.count(NameserverIPModel.id)).where(
            NameserverIPModel.nameserver_id.in_(nameserver_ids)
        )
        
        result = await db.execute(query)
        count = result.scalar_one()
        
        return count
    
    @strawberry.field
    async def count_nameservers_by_ip(
        self,
        info: Info,
        ip_id: int
    ) -> NameserverIPCount:
        """
        Count total number of nameservers for a specific IP and get list of nameserver IDs
        
        GraphQL Query Examples:
        
        # Get count and list of nameserver IDs for an IP
        {
          countNameserversByIp(ipId: 10) {
            totalNsId
            listNsId
          }
        }
        
        # Get only the count
        {
          countNameserversByIp(ipId: 10) {
            totalNsId
          }
        }
        
        # Get only the nameserver IDs list
        {
          countNameserversByIp(ipId: 10) {
            listNsId
          }
        }
        
        # Example response:
        # {
        #   "totalNsId": 5,
        #   "listNsId": [12, 25, 33, 47, 58]
        # }
        """
        db: AsyncSession = info.context["db"]
        
        # Query all nameserver-IP connections for this IP
        query = select(NameserverIPModel.nameserver_id).where(
            NameserverIPModel.ip_id == ip_id
        ).distinct().order_by(NameserverIPModel.nameserver_id)
        
        result = await db.execute(query)
        nameserver_ids = [row[0] for row in result.all()]
        
        return NameserverIPCount(
            total_ns_id=len(nameserver_ids),
            list_ns_id=nameserver_ids
        )
    
    @strawberry.field
    async def count_ips_by_nameserver(
        self,
        info: Info,
        nameserver_id: int
    ) -> IPCountByNameserver:
        """
        Count total number of IPs for a specific nameserver and get list of IP IDs
        
        NOTE: This returns a list of DISTINCT IP IDs that are associated with the given nameserver.
        Since one nameserver can have multiple records (one per IP it resolves to), this function
        will return all unique IPs for that nameserver.
        
        Example: If nameserver ID 5 has records for IPs [10, 15, 20, 10, 15], 
        this will return countIps=3 and listIps=[10, 15, 20] (distinct values only)
        
        GraphQL Query Examples:
        
        # Get count and list of IP IDs for a nameserver
        {
          countIpsByNameserver(nameserverId: 5) {
            countIps
            listIps
          }
        }
        
        # Get only the count
        {
          countIpsByNameserver(nameserverId: 5) {
            countIps
          }
        }
        
        # Get only the IP IDs list
        {
          countIpsByNameserver(nameserverId: 5) {
            listIps
          }
        }
        
        # Example response:
        # {
        #   "countIps": 3,
        #   "listIps": [10, 15, 20]
        # }
        """
        db: AsyncSession = info.context["db"]
        
        # Query all nameserver-IP connections for this nameserver
        query = select(NameserverIPModel.ip_id).where(
            NameserverIPModel.nameserver_id == nameserver_id
        ).distinct().order_by(NameserverIPModel.ip_id)
        
        result = await db.execute(query)
        ip_ids = [row[0] for row in result.all()]
        
        return IPCountByNameserver(
            count_ips=len(ip_ids),
            list_ips=ip_ids
        )
