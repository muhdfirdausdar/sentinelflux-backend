"""
History Fast Flux Analysis Query Resolvers
All query operations for HistoryFastFluxAnalysis table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ..types.history_fast_flux import HistoryFastFluxAnalysis
from ..enums import FastFluxTypeEnum
from ..utils import normalize_to_utc, get_current_utc, parse_datetime_with_timezone, convert_datetime_to_timezone, DB_TIMEZONE_NAME

# Import model
from models.history_ff_analysis import HistoryFastFluxAnalysis as HistoryFastFluxAnalysisModel


@strawberry.type
class HistoryFastFluxQuery:
    """Query operations for HistoryFastFluxAnalysis table"""
    
    @strawberry.field
    async def history_fast_flux_analysis(
        self,
        info: Info,
        domain_id: Optional[int] = None,
        flux_type: Optional[FastFluxTypeEnum] = None,
        only_latest: bool = False,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HistoryFastFluxAnalysis]:
        """
        Get historical fast flux analysis records with timezone support
        
        Parameters:
        - domain_id: Filter by specific domain ID
        - flux_type: Filter by flux type (SINGLE, DOUBLE, NONE)
        - only_latest: Return only the most recent record
        - from_datetime: Start datetime (string in any timezone format)
        - until_datetime: End datetime (string in any timezone format)
        - limit: Maximum records (only when domain_id is not given)
        - offset: Pagination offset
        
        GraphQL Query Examples:
        
        # Get latest record for domain
        {
          historyFastFluxAnalysis(domainId: 5, onlyLatest: true) {
            fluxType
            aRecordChangeFrequency
            updatedAt
          }
        }
        
        # Filter by datetime range
        {
          historyFastFluxAnalysis(
            domainId: 5,
            fromDatetime: "2025-10-01T00:00:00+08:00",
            untilDatetime: "2025-10-31T23:59:59+08:00"
          ) {
            fluxType
            aRecordChangeFrequency
            nsRecordChangeFrequency
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
        
        query = select(HistoryFastFluxAnalysisModel)
        
        # Apply filters
        conditions = []
        if domain_id:
            conditions.append(HistoryFastFluxAnalysisModel.domain_id == domain_id)
        if flux_type:
            conditions.append(HistoryFastFluxAnalysisModel.flux_type == flux_type.value)
        
        # Apply datetime range filters
        if from_dt_utc8:
            conditions.append(HistoryFastFluxAnalysisModel.updated_at >= from_dt_utc8)
        if until_dt_utc8:
            conditions.append(HistoryFastFluxAnalysisModel.updated_at <= until_dt_utc8)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(HistoryFastFluxAnalysisModel.updated_at))
        
        # Handle only_latest
        if only_latest and domain_id:
            query = query.limit(1)
        elif domain_id is None:
            query = query.offset(offset).limit(limit)
        else:
            query = query.offset(offset)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            HistoryFastFluxAnalysis(
                domain_id=r.domain_id,
                flux_type=FastFluxTypeEnum[r.flux_type.upper()],
                details=r.details,
                a_record_change_frequency=r.a_record_change_frequency,
                ns_record_change_frequency=r.ns_record_change_frequency,
                updated_at=convert_datetime_to_timezone(r.updated_at, original_timezone)
            )
            for r in records
        ]
