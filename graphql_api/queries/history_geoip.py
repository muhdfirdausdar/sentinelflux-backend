"""
History GeoIP Query Resolvers
All query operations for HistoryGeoIP table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ..types.history_geoip import HistoryGeoIP
from ..utils import normalize_to_utc, get_current_utc, parse_datetime_with_timezone, convert_datetime_to_timezone, DB_TIMEZONE_NAME

# Import model
from models.history_geoip import HistoryGeoIP as HistoryGeoIPModel


@strawberry.type
class HistoryGeoIPQuery:
    """Query operations for HistoryGeoIP table"""
    
    @strawberry.field
    async def history_geoips(
        self,
        info: Info,
        ip_id: Optional[int] = None,
        country: Optional[str] = None,
        only_latest: bool = False,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HistoryGeoIP]:
        """
        Get historical IP geolocation records with timezone support
        
        Parameters:
        - ip_id: Filter by specific IP ID
        - country: Filter by country code
        - only_latest: Return only the most recent record
        - from_datetime: Start datetime (string in any timezone format)
        - until_datetime: End datetime (string in any timezone format)
        - limit: Maximum records (only when ip_id is not given)
        - offset: Pagination offset
        
        GraphQL Query Examples:
        
        # Get latest record for IP
        {
          historyGeoips(ipId: 5, onlyLatest: true) {
            country
            continent
            updatedAt
          }
        }
        
        # Filter by datetime range
        {
          historyGeoips(
            ipId: 5,
            fromDatetime: "2025-10-01T00:00:00+08:00",
            untilDatetime: "2025-10-31T23:59:59+08:00"
          ) {
            country
            asn
            aso
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
        
        query = select(HistoryGeoIPModel)
        
        # Apply filters
        conditions = []
        if ip_id:
            conditions.append(HistoryGeoIPModel.ip_id == ip_id)
        if country:
            conditions.append(HistoryGeoIPModel.country == country)
        
        # Apply datetime range filters
        if from_dt_utc8:
            conditions.append(HistoryGeoIPModel.updated_at >= from_dt_utc8)
        if until_dt_utc8:
            conditions.append(HistoryGeoIPModel.updated_at <= until_dt_utc8)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(HistoryGeoIPModel.updated_at))
        
        # Handle only_latest
        if only_latest and ip_id:
            query = query.limit(1)
        elif ip_id is None:
            query = query.offset(offset).limit(limit)
        else:
            query = query.offset(offset)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            HistoryGeoIP(
                ip_id=r.ip_id,
                continent=r.continent,
                country=r.country,
                latitude_longitude=r.latitude_longitude,
                asn=r.asn,
                aso=r.aso,
                updated_at=convert_datetime_to_timezone(r.updated_at, original_timezone)
            )
            for r in records
        ]
    
    @strawberry.field
    async def history_geoip_at_time(
        self,
        info: Info,
        ip_id: int,
        target_datetime: str
    ) -> Optional[HistoryGeoIP]:
        """
        Get historical IP geolocation record at a specific time (±5 minutes window)
        
        This function searches for geolocation records within a 5-minute window
        (before and after) of the specified datetime. If multiple records exist
        within this window, it returns the latest one.
        
        Parameters:
        - ip_id: The IP ID to search for
        - target_datetime: Target datetime (string in any timezone format)
        
        GraphQL Query Examples:
        
        # Get geolocation at specific time
        {
          historyGeoipAtTime(
            ipId: 5,
            targetDatetime: "2025-10-15T14:30:00+08:00"
          ) {
            ipId
            country
            continent
            latitudeLongitude
            asn
            aso
            updatedAt
          }
        }
        
        # Search with different timezone
        {
          historyGeoipAtTime(
            ipId: 10,
            targetDatetime: "2025-11-01T10:00:00Z"
          ) {
            country
            asn
            aso
            updatedAt
          }
        }
        
        Returns:
        - The latest geolocation record within ±5 minutes of target datetime
        - None if no record found in that time range
        """
        db: AsyncSession = info.context["db"]
        
        # Parse and normalize the target datetime
        target_dt, target_tz = parse_datetime_with_timezone(target_datetime)
        
        # Calculate the time range: ±5 minutes
        from datetime import timedelta
        time_window = timedelta(minutes=5)
        from_dt = target_dt - time_window
        until_dt = target_dt + time_window
        
        # Query for records within the time window
        query = select(HistoryGeoIPModel).where(
            and_(
                HistoryGeoIPModel.ip_id == ip_id,
                HistoryGeoIPModel.updated_at >= from_dt,
                HistoryGeoIPModel.updated_at <= until_dt
            )
        ).order_by(desc(HistoryGeoIPModel.updated_at)).limit(1)
        
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        
        # Fallback: If no record found in ±5 minute window, get the latest record for this IP
        if not record:
            fallback_query = select(HistoryGeoIPModel).where(
                HistoryGeoIPModel.ip_id == ip_id
            ).order_by(desc(HistoryGeoIPModel.updated_at)).limit(1)
            
            fallback_result = await db.execute(fallback_query)
            record = fallback_result.scalar_one_or_none()
            
            # If still no record found, return None
            if not record:
                return None
        
        return HistoryGeoIP(
            ip_id=record.ip_id,
            continent=record.continent,
            country=record.country,
            latitude_longitude=record.latitude_longitude,
            asn=record.asn,
            aso=record.aso,
            updated_at=convert_datetime_to_timezone(record.updated_at, target_tz)
        )
