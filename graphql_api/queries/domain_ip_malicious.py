"""
Domain IP Malicious Query Resolvers
All query operations for DomainIPMalicious table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import joinedload

from ..types.domain_ip_malicious import DomainIPMalicious, DomainIPMaliciousStats

# Import models
from models.domain_ip_malicious import DomainIPMalicious as DomainIPMaliciousModel
from models.malicious_types import MaliciousType as MaliciousTypeModel
from models.sources import Sources as SourcesModel


@strawberry.type
class DomainIPMaliciousQuery:
    """Query operations for DomainIPMalicious table"""
    
    @strawberry.field
    async def domain_ip_malicious(
        self,
        info: Info,
        domain_ip_id: Optional[int] = None,
        malicious_type_id: Optional[int] = None,
        source_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DomainIPMalicious]:
        """
        Get malicious domain-IP records with optional filtering
        
        GraphQL Query Examples:
        
        # Get all malicious records
        {
          domainIpMalicious(limit: 10) {
            domainIpId
            maliciousTypeId
            maliciousName
            sourceId
            sourceName
            firstSeen
            lastSeen
          }
        }
        
        # Get malicious records for specific domain-IP connection
        {
          domainIpMalicious(domainIpId: 5) {
            maliciousTypeId
            maliciousName
            sourceId
            sourceName
            firstSeen
          }
        }
        
        # Get records by malicious type
        {
          domainIpMalicious(maliciousTypeId: 1) {
            domainIpId
            maliciousName
            sourceId
            sourceName
            lastSeen
          }
        }
        
        # Get records by source
        {
          domainIpMalicious(sourceId: 2) {
            domainIpId
            maliciousTypeId
            firstSeen
          }
        }
        
        # Combine filters
        {
          domainIpMalicious(
            domainIpId: 5, 
            maliciousTypeId: 1
          ) {
            sourceId
            firstSeen
            lastSeen
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        # Join with both malicious_types and sources tables to get names
        query = select(
            DomainIPMaliciousModel,
            MaliciousTypeModel.name,
            SourcesModel.name
        ).join(
            MaliciousTypeModel,
            DomainIPMaliciousModel.malicious_type_id == MaliciousTypeModel.id
        ).join(
            SourcesModel,
            DomainIPMaliciousModel.source_id == SourcesModel.id
        )
        
        # Apply filters
        conditions = []
        if domain_ip_id:
            conditions.append(DomainIPMaliciousModel.domain_ip_id == domain_ip_id)
        if malicious_type_id:
            conditions.append(DomainIPMaliciousModel.malicious_type_id == malicious_type_id)
        if source_id:
            conditions.append(DomainIPMaliciousModel.source_id == source_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(DomainIPMaliciousModel.last_seen)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        records = result.all()
        
        return [
            DomainIPMalicious(
                domain_ip_id=r[0].domain_ip_id,
                malicious_type_id=r[0].malicious_type_id,
                malicious_name=r[1],  # Name from malicious_types table
                source_id=r[0].source_id,
                source_name=r[2],  # Name from sources table
                first_seen=r[0].first_seen,
                last_seen=r[0].last_seen
            )
            for r in records
        ]
    
    @strawberry.field
    async def domain_ip_malicious_stats(
        self,
        info: Info,
        domain_ip_ids: List[int]
    ) -> DomainIPMaliciousStats:
        """
        Get malicious statistics for multiple domain-IP connections
        Returns total count of malicious records and distinct malicious type names
        
        GraphQL Query Examples:
        
        # Get malicious stats for single domain-IP
        {
          domainIpMaliciousStats(domainIpIds: [5]) {
            totalMalicious
            listMaliciousType
          }
        }
        
        # Get malicious stats for multiple domain-IPs
        {
          domainIpMaliciousStats(domainIpIds: [5, 10, 15, 20]) {
            totalMalicious
            listMaliciousType
          }
        }
        
        # Get only total count
        {
          domainIpMaliciousStats(domainIpIds: [5, 10, 15]) {
            totalMalicious
          }
        }
        
        # Get only malicious type names
        {
          domainIpMaliciousStats(domainIpIds: [5, 10, 15]) {
            listMaliciousType
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        if not domain_ip_ids:
            return DomainIPMaliciousStats(
                total_malicious=0,
                list_malicious_type=[]
            )
        
        # Query all malicious records for the given domain_ip_ids
        query = select(DomainIPMaliciousModel).where(
            DomainIPMaliciousModel.domain_ip_id.in_(domain_ip_ids)
        )
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Count total malicious records
        total_malicious = len(records)
        
        # Get distinct malicious_type_ids
        distinct_malicious_type_ids = list(set(r.malicious_type_id for r in records))
        
        # Fetch malicious type names for the distinct IDs
        list_malicious_type = []
        if distinct_malicious_type_ids:
            malicious_type_query = select(MaliciousTypeModel).where(
                MaliciousTypeModel.id.in_(distinct_malicious_type_ids)
            ).order_by(MaliciousTypeModel.name)
            
            malicious_type_result = await db.execute(malicious_type_query)
            malicious_types = malicious_type_result.scalars().all()
            
            list_malicious_type = [mt.name for mt in malicious_types]
        
        return DomainIPMaliciousStats(
            total_malicious=total_malicious,
            list_malicious_type=list_malicious_type
        )
