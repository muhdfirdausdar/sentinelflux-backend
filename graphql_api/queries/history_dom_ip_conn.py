"""
History Domain IP Connection Query Resolvers
All query operations for HistoryDomainIPConnection table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ..types.history_dom_ip_conn import HistoryDomainIPConnection
from ..utils import normalize_to_utc, get_current_utc, parse_datetime_with_timezone, convert_datetime_to_timezone, DB_TIMEZONE_NAME

# Import model
from models.history_dom_ip_conn import HistoryDomainIPConnection as HistoryDomainIPConnectionModel


@strawberry.type
class HistoryDomainIPConnectionQuery:
    """Query operations for HistoryDomainIPConnection table"""
    
    @strawberry.field
    async def history_domain_ip_connections(
        self,
        info: Info,
        domain_id: Optional[int] = None,
        ip_id: Optional[int] = None,
        only_latest: bool = False,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HistoryDomainIPConnection]:
        """
        Get historical domain-IP connection records with timezone support
        
        Parameters:
        - domain_id: Filter by specific domain ID
        - ip_id: Filter by specific IP ID
        - only_latest: Return only the most recent record (requires domain_id or ip_id)
        - from_datetime: Start datetime (string in any timezone format)
        - until_datetime: End datetime (string in any timezone format)
        - limit: Maximum records to return (only applies when neither domain_id nor ip_id is given)
        - offset: Pagination offset
        
        GraphQL Query Examples:
        
        # Get all history records (with limit)
        {
          historyDomainIpConnections(limit: 10) {
            domainId
            ipId
            ttl
            updatedAt
          }
        }
        
        # Get latest record for specific domain
        {
          historyDomainIpConnections(domainId: 5, onlyLatest: true) {
            ipId
            ttl
            updatedAt
          }
        }
        
        # Get all history for specific domain (no limit)
        {
          historyDomainIpConnections(domainId: 5) {
            ipId
            ttl
            updatedAt
          }
        }
        
        # Filter by datetime range with timezone
        {
          historyDomainIpConnections(
            domainId: 5,
            fromDatetime: "2025-10-01T00:00:00+08:00",
            untilDatetime: "2025-10-31T23:59:59+08:00"
          ) {
            ipId
            ttl
            updatedAt
          }
        }
        
        # Combine filters
        {
          historyDomainIpConnections(
            domainId: 5, 
            ipId: 10,
            fromDatetime: "2025-10-01T00:00:00Z"
          ) {
            ttl
            updatedAt
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        # Parse and normalize datetime parameters
        original_timezone = DB_TIMEZONE_NAME
        
        if from_datetime:
            from_dt, from_tz = parse_datetime_with_timezone(from_datetime)
            from_dt_utc8 = from_dt
            original_timezone = from_tz
        else:
            from_dt_utc8 = None
        
        if until_datetime:
            until_dt, until_tz = parse_datetime_with_timezone(until_datetime)
            until_dt_utc8 = until_dt
            if from_datetime is None:
                original_timezone = until_tz
        else:
            if from_datetime:
                until_dt_utc8 = get_current_utc()
            else:
                until_dt_utc8 = None
        
        query = select(HistoryDomainIPConnectionModel)
        
        # Apply filters
        conditions = []
        if domain_id:
            conditions.append(HistoryDomainIPConnectionModel.domain_id == domain_id)
        if ip_id:
            conditions.append(HistoryDomainIPConnectionModel.ip_id == ip_id)
        
        # Apply datetime range filters
        if from_dt_utc8:
            conditions.append(HistoryDomainIPConnectionModel.updated_at >= from_dt_utc8)
        if until_dt_utc8:
            conditions.append(HistoryDomainIPConnectionModel.updated_at <= until_dt_utc8)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(HistoryDomainIPConnectionModel.updated_at))
        
        # Handle only_latest
        if only_latest and (domain_id or ip_id):
            query = query.limit(1)
        # Apply limit only when neither domain_id nor ip_id is provided
        elif domain_id is None and ip_id is None:
            query = query.offset(offset).limit(limit)
        else:
            query = query.offset(offset)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            HistoryDomainIPConnection(
                domain_id=r.domain_id,
                ip_id=r.ip_id,
                ttl=r.ttl,
                updated_at=convert_datetime_to_timezone(r.updated_at, original_timezone)
            )
            for r in records
        ]
