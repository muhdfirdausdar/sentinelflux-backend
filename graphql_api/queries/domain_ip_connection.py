"""
Domain IP Connection Query Resolvers
All query operations for DomainIPConnection table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from ..types.domain_ip_connection import DomainIPConnection, DomainIPConnectionInfo, IPReuseInfo

# Import models
from models.domain_ip_connection import DomainIPConnection as DomainIPConnectionModel
from models.domain_ip_malicious import DomainIPMalicious as DomainIPMaliciousModel
from models.malicious_types import MaliciousType as MaliciousTypeModel
from models.sources import Sources as SourcesModel
from models.ip_geolocation import IPGeolocation as IPGeolocationModel
from models.ips import IP as IPModel


@strawberry.type
class DomainIPConnectionQuery:
    """Query operations for DomainIPConnection table"""
    
    @strawberry.field
    async def domain_ip_connections(
        self,
        info: Info,
        domain_id: Optional[int] = None,
        ip_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DomainIPConnection]:
        """
        Get domain-IP connections with optional filtering
        
        GraphQL Query Examples:
        
        # Get all connections
        {
          domainIpConnections(limit: 10) {
            id
            domainId
            ipId
            ttl
            firstSeen
            lastSeen
          }
        }
        
        # Get connections for specific domain
        {
          domainIpConnections(domainId: 5) {
            ipId
            ttl
            lowestTtl
            highestTtl
          }
        }
        
        # Get connections for specific IP
        {
          domainIpConnections(ipId: 10) {
            domainId
            ttl
            firstSeen
          }
        }
        
        # Get connections for specific domain-IP pair
        {
          domainIpConnections(domainId: 5, ipId: 10) {
            id
            ttl
            firstSeen
            lastSeen
            maliciousTypes
            maliciousSources
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(DomainIPConnectionModel)
        
        # Apply filters
        conditions = []
        if domain_id:
            conditions.append(DomainIPConnectionModel.domain_id == domain_id)
        if ip_id:
            conditions.append(DomainIPConnectionModel.ip_id == ip_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(DomainIPConnectionModel.last_seen)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        conns = result.scalars().all()
        
        # Build response with malicious information for each connection
        response = []
        for c in conns:
            # Fetch malicious information for this domain_ip_connection
            malicious_query = select(
                MaliciousTypeModel.name,
                SourcesModel.name
            ).select_from(DomainIPMaliciousModel).join(
                MaliciousTypeModel,
                DomainIPMaliciousModel.malicious_type_id == MaliciousTypeModel.id
            ).join(
                SourcesModel,
                DomainIPMaliciousModel.source_id == SourcesModel.id
            ).where(
                DomainIPMaliciousModel.domain_ip_id == c.id
            )
            
            malicious_result = await db.execute(malicious_query)
            malicious_records = malicious_result.all()
            
            # Extract unique malicious types and sources
            malicious_types = list(set(r[0] for r in malicious_records)) if malicious_records else []
            malicious_sources = list(set(r[1] for r in malicious_records)) if malicious_records else []
            
            # Fetch IP address
            ip_query = select(IPModel.ip_address).where(IPModel.id == c.ip_id)
            ip_result = await db.execute(ip_query)
            ip_addr_value = ip_result.scalar_one_or_none()
            ip_address = str(ip_addr_value) if ip_addr_value else None
            
            # Fetch geolocation info (country, asn, aso, latitude_longitude)
            geo_query = select(
                IPGeolocationModel.country,
                IPGeolocationModel.asn,
                IPGeolocationModel.aso,
                IPGeolocationModel.latitude_longitude
            ).where(
                IPGeolocationModel.ip_id == c.ip_id
            ).order_by(desc(IPGeolocationModel.last_seen)).limit(1)
            
            geo_result = await db.execute(geo_query)
            geo_data = geo_result.one_or_none()
            
            if geo_data:
                country = geo_data[0]
                asn_aso = f"AS{geo_data[1]} {geo_data[2]}"  # Format: "AS15169 Google LLC"
                latitude_longitude = geo_data[3]
            else:
                country = None
                asn_aso = None
                latitude_longitude = None
            
            response.append(
                DomainIPConnection(
                    id=c.id,
                    domain_id=c.domain_id,
                    ip_id=c.ip_id,
                    ip_address=ip_address,
                    first_seen=c.first_seen,
                    last_seen=c.last_seen,
                    ttl=c.ttl,
                    lowest_ttl=c.lowest_ttl,
                    lowest_ttl_time=c.lowest_ttl_time,
                    highest_ttl=c.highest_ttl,
                    highest_ttl_time=c.highest_ttl_time,
                    malicious_types=malicious_types,
                    malicious_sources=malicious_sources,
                    country=country,
                    asn_aso=asn_aso,
                    latitude_longitude=latitude_longitude
                )
            )
        
        return response
    
    @strawberry.field
    async def domain_ip_connection_by_id(
        self,
        info: Info,
        id: int,
        latest_only: bool = True
    ) -> List[DomainIPConnection]:
        """
        Get domain-IP connection(s) by ID
        
        GraphQL Query Examples:
        
        # Get latest connection by ID (default)
        {
          domainIpConnectionById(id: 1) {
            id
            domainId
            ipId
            ttl
            firstSeen
            lastSeen
          }
        }
        
        # Get latest connection explicitly
        {
          domainIpConnectionById(id: 1, latestOnly: true) {
            id
            domainId
            ipId
            ttl
            lastSeen
          }
        }
        
        # Get all records for this ID (historical)
        {
          domainIpConnectionById(id: 1, latestOnly: false) {
            id
            domainId
            ipId
            ttl
            firstSeen
            lastSeen
            maliciousTypes
            maliciousSources
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(DomainIPConnectionModel).where(DomainIPConnectionModel.id == id)
        
        if latest_only:
            # Get only the latest record (most recent last_seen)
            query = query.order_by(desc(DomainIPConnectionModel.last_seen)).limit(1)
        else:
            # Get all records for this ID, ordered by most recent first
            query = query.order_by(desc(DomainIPConnectionModel.last_seen))
        
        result = await db.execute(query)
        conns = result.scalars().all()
        
        # Build response with malicious information for each connection
        response = []
        for c in conns:
            # Fetch malicious information for this domain_ip_connection
            malicious_query = select(
                MaliciousTypeModel.name,
                SourcesModel.name
            ).select_from(DomainIPMaliciousModel).join(
                MaliciousTypeModel,
                DomainIPMaliciousModel.malicious_type_id == MaliciousTypeModel.id
            ).join(
                SourcesModel,
                DomainIPMaliciousModel.source_id == SourcesModel.id
            ).where(
                DomainIPMaliciousModel.domain_ip_id == c.id
            )
            
            malicious_result = await db.execute(malicious_query)
            malicious_records = malicious_result.all()
            
            # Extract unique malicious types and sources
            malicious_types = list(set(r[0] for r in malicious_records)) if malicious_records else []
            malicious_sources = list(set(r[1] for r in malicious_records)) if malicious_records else []
            
            # Fetch IP address
            ip_query = select(IPModel.ip_address).where(IPModel.id == c.ip_id)
            ip_result = await db.execute(ip_query)
            ip_addr_value = ip_result.scalar_one_or_none()
            ip_address = str(ip_addr_value) if ip_addr_value else None
            
            # Fetch geolocation info (country, asn, aso, latitude_longitude)
            geo_query = select(
                IPGeolocationModel.country,
                IPGeolocationModel.asn,
                IPGeolocationModel.aso,
                IPGeolocationModel.latitude_longitude
            ).where(
                IPGeolocationModel.ip_id == c.ip_id
            ).order_by(desc(IPGeolocationModel.last_seen)).limit(1)
            
            geo_result = await db.execute(geo_query)
            geo_data = geo_result.one_or_none()
            
            if geo_data:
                country = geo_data[0]
                asn_aso = f"AS{geo_data[1]} {geo_data[2]}"  # Format: "AS15169 Google LLC"
                latitude_longitude = geo_data[3]
            else:
                country = None
                asn_aso = None
                latitude_longitude = None
            
            response.append(
                DomainIPConnection(
                    id=c.id,
                    domain_id=c.domain_id,
                    ip_id=c.ip_id,
                    ip_address=ip_address,
                    first_seen=c.first_seen,
                    last_seen=c.last_seen,
                    ttl=c.ttl,
                    lowest_ttl=c.lowest_ttl,
                    lowest_ttl_time=c.lowest_ttl_time,
                    highest_ttl=c.highest_ttl,
                    highest_ttl_time=c.highest_ttl_time,
                    malicious_types=malicious_types,
                    malicious_sources=malicious_sources,
                    country=country,
                    asn_aso=asn_aso,
                    latitude_longitude=latitude_longitude
                )
            )
        
        return response

    @strawberry.field
    async def domain_ip_connection_info_by_id(
        self,
        info: Info,
        domain_id: int
    ) -> DomainIPConnectionInfo:
        """
        Get aggregated information about all IP connections for a specific domain
        
        GraphQL Query Examples:
        
        # Get connection stats for domain
        {
          domainIpConnectionInfoById(domainId: 5) {
            domainId
            totalIps
            firstSeen
            lastSeen
            latestTtl
            lowestTtl
            highestTtl
            lowestTtlTime
            highestTtlTime
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        # Get all connections for this domain
        query = select(DomainIPConnectionModel).where(
            DomainIPConnectionModel.domain_id == domain_id
        )
        result = await db.execute(query)
        connections = result.scalars().all()
        
        if not connections:
            # Return default values if no connections found
            from datetime import datetime
            return DomainIPConnectionInfo(
                domain_id=domain_id,
                total_ips=0,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                latest_ttl=0,
                lowest_ttl=0,
                highest_ttl=0,
                lowest_ttl_time=datetime.now(),
                highest_ttl_time=datetime.now()
            )
        
        # Calculate aggregated values
        # totalIPs - count distinct connections
        total_ips = len(connections)
        
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
        
        # listCountry - distinct list of countries from all IPs
        countries = []
        for c in connections:
            geo_query = select(IPGeolocationModel.country).where(
                IPGeolocationModel.ip_id == c.ip_id
            ).order_by(desc(IPGeolocationModel.last_seen)).limit(1)
            
            geo_result = await db.execute(geo_query)
            country = geo_result.scalar_one_or_none()
            if country:
                countries.append(country)
        
        # Get distinct countries
        list_country = list(set(countries))
        
        return DomainIPConnectionInfo(
            domain_id=domain_id,
            total_ips=total_ips,
            first_seen=first_seen,
            last_seen=last_seen,
            latest_ttl=latest_ttl,
            lowest_ttl=lowest_ttl,
            highest_ttl=highest_ttl,
            lowest_ttl_time=lowest_ttl_time,
            highest_ttl_time=highest_ttl_time,
            list_country=list_country
        )

    @strawberry.field
    async def count_total_domain_by_ip_id(
        self,
        info: Info,
        ip_id_list: List[int],
        excluded_domain_id: int
    ) -> List[IPReuseInfo]:
        """
        Count how many domains are using each IP (excluding a specific domain).
        Useful for detecting shared hosting or suspicious IP reuse patterns.
        
        Parameters:
        - ip_id_list: List of IP IDs to check
        - excluded_domain_id: Domain ID to exclude from the count
        
        Returns:
        - List of IPReuseInfo with ip_id, total_domain_reused, and list_domain
        
        GraphQL Query Examples:
        
        # Check if IPs are shared with other domains
        {
          countTotalDomainByIpId(
            ipIdList: [10, 15, 20],
            excludedDomainId: 5
          ) {
            ipId
            totalDomainReused
            listDomain
          }
        }
        
        # Example response:
        # [
        #   {
        #     "ipId": 10,
        #     "totalDomainReused": 3,
        #     "listDomain": [8, 12, 25]
        #   },
        #   {
        #     "ipId": 15,
        #     "totalDomainReused": 0,
        #     "listDomain": []
        #   },
        #   {
        #     "ipId": 20,
        #     "totalDomainReused": 1,
        #     "listDomain": [42]
        #   }
        # ]
        """
        db: AsyncSession = info.context["db"]
        
        result_list = []
        
        # Process each IP ID
        for ip_id in ip_id_list:
            # Query to find all domains using this IP, excluding the specified domain
            query = select(DomainIPConnectionModel.domain_id).where(
                and_(
                    DomainIPConnectionModel.ip_id == ip_id,
                    DomainIPConnectionModel.domain_id != excluded_domain_id
                )
            ).distinct()
            
            result = await db.execute(query)
            domain_ids = [row[0] for row in result.all()]
            
            # Count and create response
            result_list.append(
                IPReuseInfo(
                    ip_id=ip_id,
                    total_domain_reused=len(domain_ids),
                    list_domain=domain_ids
                )
            )
        
        return result_list
    
    @strawberry.field
    async def get_domain_ip_ids_by_domain(
        self,
        info: Info,
        domain_id: int
    ) -> List[int]:
        """
        Get list of domain_ip_connection IDs for a specific domain
        
        GraphQL Query Examples:
        
        # Get all domain-IP connection IDs for a domain
        {
          getDomainIpIdsByDomain(domainId: 5)
        }
        
        # Example response:
        # [1, 5, 12, 23, 45, 67]
        """
        db: AsyncSession = info.context["db"]
        
        # Query to get all domain_ip_connection IDs for this domain
        query = select(DomainIPConnectionModel.id).where(
            DomainIPConnectionModel.domain_id == domain_id
        ).order_by(DomainIPConnectionModel.id)
        
        result = await db.execute(query)
        domain_ip_ids = [row[0] for row in result.all()]
        
        return domain_ip_ids
    
    @strawberry.field
    async def get_ip_ids_by_domain(
        self,
        info: Info,
        domain_id: int
    ) -> List[int]:
        """
        Get list of IP IDs associated with a specific domain
        
        GraphQL Query Examples:
        
        # Get all IP IDs for a domain
        {
          getIpIdsByDomain(domainId: 5)
        }
        
        # Example response:
        # [10, 15, 20, 33, 45]
        """
        db: AsyncSession = info.context["db"]
        
        # Query to get all IP IDs for this domain
        query = select(DomainIPConnectionModel.ip_id).where(
            DomainIPConnectionModel.domain_id == domain_id
        ).distinct().order_by(DomainIPConnectionModel.ip_id)
        
        result = await db.execute(query)
        ip_ids = [row[0] for row in result.all()]
        
        return ip_ids
