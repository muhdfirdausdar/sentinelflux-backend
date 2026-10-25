"""
Domain Query Resolvers
All query operations for Domain table
"""
from typing import Optional
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, asc, func, select

from ..types import Domain, DomainResponse
from ..filters import DomainFilterInput, DomainSortInput, StringFilter, IntFilter, DateFilter
from ..enums import (
    DomainStatusEnum, SortOrder, StringOperator, 
    NumberOperator, DateOperator
)

# Import models
from models.domain import Domain as DomainModel
from models.fast_flux_analysis import FastFluxAnalysis as FastFluxAnalysisModel
from utils.input_sanitizer import InputSanitizer


@strawberry.type
class DomainQuery:
    """Query operations for Domain table"""
    
    @strawberry.field
    async def domains(
        self,
        info: Info,
        filter: Optional[DomainFilterInput] = None,
        sort: Optional[DomainSortInput] = None,
        limit: int = 20,
        offset: int = 0
    ) -> DomainResponse:
        """
        Get domains with advanced filtering, sorting, and pagination
        
        Examples:
        - Get active domains: filter: { status: ACTIVE }
        - Get domains with high analysis count: filter: { total_analysis_done: { value: 10, operator: GTE } }
        - Search domains: filter: { search: "google" }
        - Get recent domains: sort: { field: "first_seen", order: DESC }
        """
        db: AsyncSession = info.context["db"]
        
        # Base query using select()
        query = select(DomainModel)
        
        # Apply filters
        if filter:
            query = self._apply_domain_filters(query, filter)
        
        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply sorting
        if sort:
            sort_field = getattr(DomainModel, sort.field, None)
            if sort_field:
                if sort.order == SortOrder.DESC:
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(asc(sort_field))
            else:
                # Default sort by id desc
                query = query.order_by(desc(DomainModel.id))
        else:
            # Default sort by id desc
            query = query.order_by(desc(DomainModel.id))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        domains = result.scalars().all()
        
        # Convert to GraphQL types
        domain_list = [
            Domain(
                id=d.id,
                domain_name=d.domain_name,
                first_seen=d.first_seen,
                last_seen=d.last_seen,
                status=DomainStatusEnum[d.status.upper()],
                source_id=d.source_id,
                last_ff_analysis=d.last_ff_analysis,
                total_analysis_done=d.total_analysis_done,
                domain_analysis_type=d.domain_analysis_type,
                wait_to_ff_analysis=d.wait_to_ff_analysis,
                is_unrated=d.is_unrated,
                remarks=d.remarks
            )
            for d in domains
        ]
        
        return DomainResponse(
            items=domain_list,
            total_count=total_count
        )
    
    @strawberry.field
    async def domain_by_id(
        self,
        info: Info,
        id: int
    ) -> Optional[Domain]:
        """
        Get a specific domain by ID
        
        GraphQL Query Examples:
        
        # Get domain by ID
        {
          domainById(id: 5) {
            id
            domainName
            status
            firstSeen
            lastSeen
            totalAnalysisDone
            remarks
          }
        }
        
        # Get domain with relationships
        {
          domainById(id: 5) {
            id
            domainName
            status
            source {
              id
              name
            }
            fastFluxAnalysis(limit: 3) {
              id
              fluxType
              detectedOn
            }
          }
        }
        
        # Returns null if not found
        {
          domainById(id: 999) {
            id
            domainName
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(DomainModel).where(DomainModel.id == id)
        result = await db.execute(query)
        domain = result.scalar_one_or_none()
        
        if not domain:
            return None
        
        return Domain(
            id=domain.id,
            domain_name=domain.domain_name,
            first_seen=domain.first_seen,
            last_seen=domain.last_seen,
            status=DomainStatusEnum[domain.status.upper()],
            source_id=domain.source_id,
            last_ff_analysis=domain.last_ff_analysis,
            total_analysis_done=domain.total_analysis_done,
            domain_analysis_type=domain.domain_analysis_type,
            wait_to_ff_analysis=domain.wait_to_ff_analysis,
            is_unrated=domain.is_unrated,
            remarks=domain.remarks
        )
    
    def _apply_domain_filters(self, query, filter: DomainFilterInput):
        """Helper method to apply complex filters to domain query"""
        conditions = []
        
        # String filters
        if filter.domain_name:
            # Sanitize domain_name filter value to prevent invalid or malicious input
            try:
                filter.domain_name.value = InputSanitizer.sanitize_domain_search(filter.domain_name.value)
            except ValueError as e:
                raise ValueError(f"Invalid domain_name filter: {e}")

            conditions.append(
                self._apply_string_filter(DomainModel.domain_name, filter.domain_name)
            )
        
        if filter.domain_analysis_type:
            conditions.append(
                self._apply_string_filter(DomainModel.domain_analysis_type, filter.domain_analysis_type)
            )
        
        if filter.remarks:
            conditions.append(
                self._apply_string_filter(DomainModel.remarks, filter.remarks)
            )
        
        # Status filters
        if filter.status:
            conditions.append(DomainModel.status == filter.status.value)
        
        if filter.status_in:
            status_values = [s.value for s in filter.status_in]
            conditions.append(DomainModel.status.in_(status_values))
        
        # Number filters
        if filter.id:
            conditions.append(self._apply_number_filter(DomainModel.id, filter.id))
        
        if filter.source_id:
            conditions.append(self._apply_number_filter(DomainModel.source_id, filter.source_id))
        
        if filter.total_analysis_done:
            conditions.append(
                self._apply_number_filter(DomainModel.total_analysis_done, filter.total_analysis_done)
            )
        
        # Date filters
        if filter.first_seen:
            conditions.append(self._apply_date_filter(DomainModel.first_seen, filter.first_seen))
        
        if filter.last_seen:
            conditions.append(self._apply_date_filter(DomainModel.last_seen, filter.last_seen))
        
        if filter.last_ff_analysis:
            conditions.append(
                self._apply_date_filter(DomainModel.last_ff_analysis, filter.last_ff_analysis)
            )
        
        # Boolean filters
        if filter.wait_to_ff_analysis is not None:
            conditions.append(DomainModel.wait_to_ff_analysis == filter.wait_to_ff_analysis)
        
        if filter.is_unrated is not None:
            conditions.append(DomainModel.is_unrated == filter.is_unrated)
        
        # Relationship filters
        if filter.has_source is not None:
            if filter.has_source:
                conditions.append(DomainModel.source_id.isnot(None))
            else:
                conditions.append(DomainModel.source_id.is_(None))
        
        if filter.has_ff_analysis is not None:
            if filter.has_ff_analysis:
                query = query.join(FastFluxAnalysisModel)
            else:
                query = query.outerjoin(FastFluxAnalysisModel).where(
                    FastFluxAnalysisModel.id.is_(None)
                )
        
        if filter.flux_type:
            query = query.join(FastFluxAnalysisModel).where(
                FastFluxAnalysisModel.flux_type == filter.flux_type.value
            )
        
        # Search across multiple fields
        if filter.search:
            # Attempt to sanitize search term for domain_name matching; if invalid, skip domain_name match
            domain_search_condition = None
            try:
                sanitized = InputSanitizer.sanitize_domain_search(filter.search)
                domain_search_condition = DomainModel.domain_name.ilike(f"%{sanitized}%")
            except ValueError:
                domain_search_condition = None

            # Remarks and analysis_type are free-text fields; keep their existing behavior
            search_term = f"%{filter.search}%"
            search_conditions = []
            if domain_search_condition is not None:
                search_conditions.append(domain_search_condition)
            search_conditions.extend([
                DomainModel.remarks.ilike(search_term),
                DomainModel.domain_analysis_type.ilike(search_term)
            ])

            conditions.append(or_(*search_conditions))
        
        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))
        
        # Distinct if joined
        if filter.has_ff_analysis or filter.flux_type:
            query = query.distinct()
        
        return query
    
    def _apply_string_filter(self, field, string_filter: StringFilter):
        """Apply string comparison operators"""
        value = string_filter.value
        
        # Handle case sensitivity
        if not string_filter.case_sensitive:
            field = func.lower(field)
            value = value.lower()
        
        if string_filter.operator == StringOperator.EQUALS:
            return field == value
        elif string_filter.operator == StringOperator.NOT_EQUALS:
            return field != value
        elif string_filter.operator == StringOperator.CONTAINS:
            return field.like(f"%{value}%") if string_filter.case_sensitive else field.ilike(f"%{value}%")
        elif string_filter.operator == StringOperator.STARTS_WITH:
            return field.like(f"{value}%") if string_filter.case_sensitive else field.ilike(f"{value}%")
        elif string_filter.operator == StringOperator.ENDS_WITH:
            return field.like(f"%{value}") if string_filter.case_sensitive else field.ilike(f"%{value}")
        else:
            return field == value
    
    def _apply_number_filter(self, field, number_filter: IntFilter):
        """Apply numeric comparison operators"""
        if number_filter.operator == NumberOperator.EQUALS:
            return field == number_filter.value
        elif number_filter.operator == NumberOperator.NOT_EQUALS:
            return field != number_filter.value
        elif number_filter.operator == NumberOperator.GREATER_THAN:
            return field > number_filter.value
        elif number_filter.operator == NumberOperator.GREATER_THAN_OR_EQUAL:
            return field >= number_filter.value
        elif number_filter.operator == NumberOperator.LESS_THAN:
            return field < number_filter.value
        elif number_filter.operator == NumberOperator.LESS_THAN_OR_EQUAL:
            return field <= number_filter.value
        elif number_filter.operator == NumberOperator.BETWEEN:
            return and_(
                field >= number_filter.min_value,
                field <= number_filter.max_value
            )
        else:
            return field == number_filter.value
    
    def _apply_date_filter(self, field, date_filter: DateFilter):
        """Apply date comparison operators"""
        if date_filter.operator == DateOperator.EQUALS:
            return field == date_filter.value
        elif date_filter.operator == DateOperator.NOT_EQUALS:
            return field != date_filter.value
        elif date_filter.operator == DateOperator.AFTER:
            return field > date_filter.value
        elif date_filter.operator == DateOperator.AFTER_OR_ON:
            return field >= date_filter.value
        elif date_filter.operator == DateOperator.BEFORE:
            return field < date_filter.value
        elif date_filter.operator == DateOperator.BEFORE_OR_ON:
            return field <= date_filter.value
        elif date_filter.operator == DateOperator.BETWEEN:
            return and_(
                field >= date_filter.start_date,
                field <= date_filter.end_date
            )
        else:
            return field == date_filter.value
