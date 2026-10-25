"""
History Nameserver IP Query Resolvers
All query operations for HistoryNameserverIP table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ..types.history_ns_ip import HistoryNameserverIP
from ..utils import normalize_to_utc, get_current_utc, parse_datetime_with_timezone, convert_datetime_to_timezone, DB_TIMEZONE_NAME

# Import model
from models.history_ns_ip import HistoryNameserverIP as HistoryNameserverIPModel


@strawberry.type
class HistoryNameserverIPQuery:
    """Query operations for HistoryNameserverIP table"""
    
    @strawberry.field
    async def history_nameserver_ips(
        self,
        info: Info,
        ip_id: Optional[int] = None,
        nameserver_id: Optional[int] = None,
        only_latest: bool = False,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HistoryNameserverIP]:
        """
        Get historical nameserver-IP connection records with timezone support
        
        Parameters:
        - ip_id: Filter by specific IP ID
        - nameserver_id: Filter by specific nameserver ID
        - only_latest: Return only the most recent record
        - from_datetime: Start datetime (string in any timezone format)
        - until_datetime: End datetime (string in any timezone format)
        - limit: Maximum records (only when neither ip_id nor nameserver_id is given)
        - offset: Pagination offset
        
        GraphQL Query Examples:
        
        # Get latest record
        {
          historyNameserverIps(ipId: 5, onlyLatest: true) {
            nameserverId
            ttl
            updatedAt
          }
        }
        
        # Filter by datetime range
        {
          historyNameserverIps(
            ipId: 5,
            fromDatetime: "2025-10-01T00:00:00+08:00",
            untilDatetime: "2025-10-31T23:59:59+08:00"
          ) {
            nameserverId
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
        
        query = select(HistoryNameserverIPModel)
        
        # Apply filters
        conditions = []
        if ip_id:
            conditions.append(HistoryNameserverIPModel.ip_id == ip_id)
        if nameserver_id:
            conditions.append(HistoryNameserverIPModel.nameserver_id == nameserver_id)
        
        # Apply datetime range filters
        if from_dt_utc8:
            conditions.append(HistoryNameserverIPModel.updated_at >= from_dt_utc8)
        if until_dt_utc8:
            conditions.append(HistoryNameserverIPModel.updated_at <= until_dt_utc8)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(HistoryNameserverIPModel.updated_at))
        
        # Handle only_latest
        if only_latest and (ip_id or nameserver_id):
            query = query.limit(1)
        elif ip_id is None and nameserver_id is None:
            query = query.offset(offset).limit(limit)
        else:
            query = query.offset(offset)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            HistoryNameserverIP(
                ip_id=r.ip_id,
                nameserver_id=r.nameserver_id,
                ttl=r.ttl,
                updated_at=convert_datetime_to_timezone(r.updated_at, original_timezone)
            )
            for r in records
        ]
