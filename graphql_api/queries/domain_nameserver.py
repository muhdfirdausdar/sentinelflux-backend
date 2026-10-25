"""
Domain Nameserver Query Resolvers
All query operations for DomainNameserver table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from ..types.domain_nameserver import DomainNameserver, DomainNameserverInfo, DomainNameserverCount

# Import models
from models.domain_nameserver import DomainNameserver as DomainNameserverModel
from models.nameserver_ip import NameserverIP as NameserverIPModel
from models.ip_geolocation import IPGeolocation as IPGeolocationModel


@strawberry.type
class DomainNameserverQuery:
    """Query operations for DomainNameserver table"""
    
    @strawberry.field
    async def domain_nameservers(
        self,
        info: Info,
        domain_id: Optional[int] = None,
        nameserver_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DomainNameserver]:
        """
        Get domain-nameserver connections with optional filtering
        
        GraphQL Query Examples:
        
        # Get all connections
        {
          domainNameservers(limit: 10) {
            id
            domainId
            nameserverId
            ttl
            firstSeen
            lastSeen
          }
        }
        
        # Get nameservers for specific domain
        {
          domainNameservers(domainId: 5) {
            nameserverId
            ttl
            firstSeen
          }
        }
        
        # Get domains using specific nameserver
        {
          domainNameservers(nameserverId: 10) {
            domainId
            ttl
            lastSeen
            countries
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(DomainNameserverModel)
        
        # Apply filters
        conditions = []
        if domain_id:
            conditions.append(DomainNameserverModel.domain_id == domain_id)
        if nameserver_id:
            conditions.append(DomainNameserverModel.nameserver_id == nameserver_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(DomainNameserverModel.last_seen)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        conns = result.scalars().all()
        
        # Build response with country information for each connection
        response = []
        for c in conns:
            # Fetch countries for this nameserver's IPs
            # Get all IPs associated with this nameserver
            ns_ip_query = select(NameserverIPModel.ip_id).where(
                NameserverIPModel.nameserver_id == c.nameserver_id
            )
            ns_ip_result = await db.execute(ns_ip_query)
            ip_ids = [row[0] for row in ns_ip_result.all()]
            
            # Get countries for these IPs
            countries = []
            if ip_ids:
                geo_query = select(IPGeolocationModel.country).where(
                    IPGeolocationModel.ip_id.in_(ip_ids)
                ).distinct()
                
                geo_result = await db.execute(geo_query)
                countries = [row[0] for row in geo_result.all() if row[0]]
            
            response.append(
                DomainNameserver(
                    id=c.id,
                    domain_id=c.domain_id,
                    nameserver_id=c.nameserver_id,
                    first_seen=c.first_seen,
                    last_seen=c.last_seen,
                    ttl=c.ttl,
                    lowest_ttl=c.lowest_ttl,
                    lowest_ttl_time=c.lowest_ttl_time,
                    highest_ttl=c.highest_ttl,
                    highest_ttl_time=c.highest_ttl_time,
                    countries=countries
                )
            )
        
        return response
    
    @strawberry.field
    async def domain_nameserver_by_id(
        self,
        info: Info,
        id: int,
        latest_only: bool = True
    ) -> List[DomainNameserver]:
        """
        Get domain-nameserver connection(s) by ID
        
        GraphQL Query Examples:
        
        # Get latest connection by ID (default)
        {
          domainNameserverById(id: 1) {
            id
            domainId
            nameserverId
            ttl
            countries
            firstSeen
            lastSeen
          }
        }
        
        # Get latest connection explicitly
        {
          domainNameserverById(id: 1, latestOnly: true) {
            id
            domainId
            nameserverId
            ttl
            countries
            lastSeen
          }
        }
        
        # Get all records for this ID (historical)
        {
          domainNameserverById(id: 1, latestOnly: false) {
            id
            domainId
            nameserverId
            ttl
            countries
            firstSeen
            lastSeen
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(DomainNameserverModel).where(DomainNameserverModel.id == id)
        
        if latest_only:
            # Get only the latest record (most recent last_seen)
            query = query.order_by(desc(DomainNameserverModel.last_seen)).limit(1)
        else:
            # Get all records for this ID, ordered by most recent first
            query = query.order_by(desc(DomainNameserverModel.last_seen))
        
        result = await db.execute(query)
        conns = result.scalars().all()
        
        # Build response with country information for each connection
        response = []
        for c in conns:
            # Fetch countries for this nameserver's IPs
            # Get all IPs associated with this nameserver
            ns_ip_query = select(NameserverIPModel.ip_id).where(
                NameserverIPModel.nameserver_id == c.nameserver_id
            )
            ns_ip_result = await db.execute(ns_ip_query)
            ip_ids = [row[0] for row in ns_ip_result.all()]
            
            # Get countries for these IPs
            countries = []
            if ip_ids:
                geo_query = select(IPGeolocationModel.country).where(
                    IPGeolocationModel.ip_id.in_(ip_ids)
                ).distinct()
                
                geo_result = await db.execute(geo_query)
                countries = [row[0] for row in geo_result.all() if row[0]]
            
            response.append(
                DomainNameserver(
                    id=c.id,
                    domain_id=c.domain_id,
                    nameserver_id=c.nameserver_id,
                    first_seen=c.first_seen,
                    last_seen=c.last_seen,
                    ttl=c.ttl,
                    lowest_ttl=c.lowest_ttl,
                    lowest_ttl_time=c.lowest_ttl_time,
                    highest_ttl=c.highest_ttl,
                    highest_ttl_time=c.highest_ttl_time,
                    countries=countries
                )
            )
        
        return response

    @strawberry.field
    async def count_domain_nameservers(
        self,
        info: Info,
        domain_id: int
    ) -> DomainNameserverCount:
        """
        Count total number of nameservers for a specific domain and get list of nameserver IDs
        
        GraphQL Query Examples:
        
        # Get count and list of nameserver IDs for domain
        {
          countDomainNameservers(domainId: 5) {
            count
            nameserverIds
          }
        }
        
        # Get only the count
        {
          countDomainNameservers(domainId: 5) {
            count
          }
        }
        
        # Get only the nameserver IDs
        {
          countDomainNameservers(domainId: 5) {
            nameserverIds
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        # Get all nameserver connections for this domain
        query = select(DomainNameserverModel).where(
            DomainNameserverModel.domain_id == domain_id
        )
        
        result = await db.execute(query)
        connections = result.scalars().all()
        
        # Extract nameserver IDs
        nameserver_ids = [c.nameserver_id for c in connections if c.nameserver_id is not None]
        
        return DomainNameserverCount(
            count=len(nameserver_ids),
            nameserver_ids=nameserver_ids
        )

    @strawberry.field
    async def domain_nameserver_info_by_id(
        self,
        info: Info,
        domain_id: int
    ) -> DomainNameserverInfo:
        """
        Get aggregated information about all nameserver connections for a specific domain
        
        GraphQL Query Examples:
        
        # Get nameserver stats for domain
        {
          domainNameserverInfoById(domainId: 5) {
            domainId
            totalNameservers
            firstSeen
            lastSeen
            latestTtl
            lowestTtl
            highestTtl
            lowestTtlTime
            highestTtlTime
            listCountry
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        # Get all nameserver connections for this domain
        query = select(DomainNameserverModel).where(
            DomainNameserverModel.domain_id == domain_id
        )
        result = await db.execute(query)
        connections = result.scalars().all()
        
        if not connections:
            # Return default values if no connections found
            from datetime import datetime
            return DomainNameserverInfo(
                domain_id=domain_id,
                total_nameservers=0,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                latest_ttl=0,
                lowest_ttl=0,
                highest_ttl=0,
                lowest_ttl_time=datetime.now(),
                highest_ttl_time=datetime.now(),
                list_country=[]
            )
        
        # Calculate aggregated values
        # totalNameservers - count distinct connections
        total_nameservers = len(connections)
        
        # firstSeen - earliest first_seen
        first_seen = min(c.first_seen for c in connections)
        
        # lastSeen - most recent last_seen
        last_seen = max(c.last_seen for c in connections)
        
        # latestTTL - TTL from most recent connection
        latest_connection = max(connections, key=lambda c: c.last_seen)
        latest_ttl = latest_connection.ttl
        
        # lowestTTL - minimum lowest_ttl value
        lowest_ttl = min(c.lowest_ttl for c in connections)
        
        # highestTTL - maximum highest_ttl value
        highest_ttl = max(c.highest_ttl for c in connections)
        
        # lowestTTLTime - from connection with lowest TTL
        connection_with_lowest_ttl = min(connections, key=lambda c: c.lowest_ttl)
        lowest_ttl_time = connection_with_lowest_ttl.lowest_ttl_time
        
        # highestTTLTime - from connection with highest TTL
        connection_with_highest_ttl = max(connections, key=lambda c: c.highest_ttl)
        highest_ttl_time = connection_with_highest_ttl.highest_ttl_time
        
        # listCountry - distinct list of countries from all nameserver IPs
        all_countries = []
        for c in connections:
            # Get all IPs associated with this nameserver
            ns_ip_query = select(NameserverIPModel.ip_id).where(
                NameserverIPModel.nameserver_id == c.nameserver_id
            )
            ns_ip_result = await db.execute(ns_ip_query)
            ip_ids = [row[0] for row in ns_ip_result.all()]
            
            # Get countries for these IPs
            if ip_ids:
                geo_query = select(IPGeolocationModel.country).where(
                    IPGeolocationModel.ip_id.in_(ip_ids)
                ).distinct()
                
                geo_result = await db.execute(geo_query)
                countries = [row[0] for row in geo_result.all() if row[0]]
                all_countries.extend(countries)
        
        # Get distinct countries
        list_country = list(set(all_countries))
        
        return DomainNameserverInfo(
            domain_id=domain_id,
            total_nameservers=total_nameservers,
            first_seen=first_seen,
            last_seen=last_seen,
            latest_ttl=latest_ttl,
            lowest_ttl=lowest_ttl,
            highest_ttl=highest_ttl,
            lowest_ttl_time=lowest_ttl_time,
            highest_ttl_time=highest_ttl_time,
            list_country=list_country
        )
