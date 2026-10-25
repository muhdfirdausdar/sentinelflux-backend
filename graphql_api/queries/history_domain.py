"""
History Domain Query Resolvers
All query operations for HistoryDomain table
"""
from typing import Optional, List
from datetime import datetime
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ..types.history_domain import HistoryDomain
from ..enums import DomainStatusEnum
from ..utils import normalize_to_utc, get_current_utc, parse_datetime_with_timezone, convert_datetime_to_timezone, DB_TIMEZONE_NAME

# Import model
from models.history_domain import HistoryDomain as HistoryDomainModel


@strawberry.type
class HistoryDomainQuery:
    """Query operations for HistoryDomain table"""
    
    @strawberry.field
    async def history_domains(
        self,
        info: Info,
        domain_id: Optional[int] = None,
        status: Optional[DomainStatusEnum] = None,
        only_latest: bool = False,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HistoryDomain]:
        """
        Get historical domain records with optional filtering and timezone support
        
        Parameters:
        - domain_id: Filter by specific domain ID
        - status: Filter by domain status
        - only_latest: Return only the most recent record for the domain (requires domain_id)
        - from_datetime: Start datetime (string in any timezone format)
        - until_datetime: End datetime (string in any timezone format)
        - limit: Maximum records to return (only applies when domain_id is not given)
        - offset: Pagination offset
        
        Datetime Handling:
        - Accepts datetime strings in any timezone format
        - Converts to UTC+8 for database queries (database timezone)
        - Returns datetime in original timezone format
        - If only from_datetime is provided, until_datetime defaults to now()
        - If only until_datetime is provided, fetches all records before that time
        
        GraphQL Query Examples:
        
        # Get all history records (with limit)
        {
          historyDomains(limit: 10) {
            domainId
            status
            updatedAt
            remarks
          }
        }
        
        # Get latest record for specific domain
        {
          historyDomains(domainId: 5, onlyLatest: true) {
            domainId
            status
            updatedAt
            remarks
          }
        }
        
        # Get all history for specific domain (no limit)
        {
          historyDomains(domainId: 5) {
            status
            updatedAt
            remarks
          }
        }
        
        # Filter by datetime range
        {
          historyDomains(
            domainId: 5,
            fromDatetime: "2025-10-01T00:00:00+08:00",
            untilDatetime: "2025-10-31T23:59:59+08:00"
          ) {
            status
            updatedAt
          }
        }
        
        # Get records from specific date onwards
        {
          historyDomains(
            domainId: 5,
            fromDatetime: "2025-10-01T00:00:00Z"
          ) {
            status
            updatedAt
          }
        }
        
        # Get records before specific date
        {
          historyDomains(
            domainId: 5,
            untilDatetime: "2025-10-31T23:59:59+00:00"
          ) {
            status
            updatedAt
          }
        }
        
        # Filter by status
        {
          historyDomains(status: ACTIVE, limit: 10) {
            domainId
            status
            updatedAt
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        # Parse and normalize datetime parameters
        # Determine the timezone to return results in
        original_timezone = DB_TIMEZONE_NAME  # Default to database timezone (UTC+8)
        
        if from_datetime:
            from_dt, from_tz = parse_datetime_with_timezone(from_datetime)
            from_dt_utc8 = from_dt
            original_timezone = from_tz  # Use timezone from from_datetime
        else:
            from_dt_utc8 = None
        
        if until_datetime:
            until_dt, until_tz = parse_datetime_with_timezone(until_datetime)
            until_dt_utc8 = until_dt
            # If no from_datetime, use timezone from until_datetime
            if from_datetime is None:
                original_timezone = until_tz
            # If both are provided, prefer from_datetime timezone (already set above)
        else:
            # If from_datetime is provided but until_datetime is not, default to now
            if from_datetime:
                until_dt_utc8 = get_current_utc()
            else:
                until_dt_utc8 = None
        
        query = select(HistoryDomainModel)
        
        # Apply filters
        conditions = []
        if domain_id:
            conditions.append(HistoryDomainModel.domain_id == domain_id)
        if status:
            conditions.append(HistoryDomainModel.status == status.value)
        
        # Apply datetime range filters
        if from_dt_utc8:
            conditions.append(HistoryDomainModel.updated_at >= from_dt_utc8)
        if until_dt_utc8:
            conditions.append(HistoryDomainModel.updated_at <= until_dt_utc8)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by most recent first
        query = query.order_by(desc(HistoryDomainModel.updated_at))
        
        # Handle only_latest
        if only_latest and domain_id:
            query = query.limit(1)
        # Apply limit only when domain_id is not provided
        elif domain_id is None:
            query = query.offset(offset).limit(limit)
        else:
            # domain_id is provided but only_latest is False - no limit
            query = query.offset(offset)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Convert datetimes back to original timezone
        return [
            HistoryDomain(
                domain_id=r.domain_id,
                updated_at=convert_datetime_to_timezone(r.updated_at, original_timezone),
                status=DomainStatusEnum[r.status.upper()],
                remarks=r.remarks
            )
            for r in records
        ]
