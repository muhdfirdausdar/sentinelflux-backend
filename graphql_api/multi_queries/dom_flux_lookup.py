"""
For page: Domain Fast Flux Lookup
Show a little bit summary of domains with fast flux analysis
This module combines existing queries from other modules
"""

from typing import Optional, List
import strawberry
from strawberry.types import Info
from strawberry.scalars import JSON
from sqlalchemy.ext.asyncio import AsyncSession

# Import types
from ..enums import DomainStatusEnum, StringOperator

# Import existing query classes to reuse their functions
from ..queries.domain import DomainQuery
from ..queries.history_domain import HistoryDomainQuery
from ..queries.history_fast_flux import HistoryFastFluxQuery
from ..queries.domain_ip_connection import DomainIPConnectionQuery

# Import filters
from ..filters import DomainFilterInput, StringFilter
from utils.input_sanitizer import InputSanitizer


@strawberry.type
class IPReuseData:
    """IP reuse information"""
    ip_id: int
    total_domain_reused: int


@strawberry.type
class DomainStatusRecord:
    """Single domain status history record"""
    updated_at: str
    status: DomainStatusEnum


@strawberry.type
class DomainFluxRecord:
    """Single fast flux history record"""
    updated_at: str
    flux_type: str

@strawberry.type
class DomainFluxHistoryResult:
    """Historical records for domain status and flux analysis"""
    domain_id: int
    domain_status: JSON  # Dict[str, DomainStatusRecord]
    domain_flux: JSON  # Dict[str, DomainFluxRecord]



@strawberry.type
class DomainFluxLookupResult:
    """Combined result for domain fast flux lookup"""
    # Domain info
    domain_id: int
    status: DomainStatusEnum
    
    # Fast flux analysis history
    fast_flux_first_analysis: Optional[str]
    fast_flux_last_analysis: Optional[str]
    fast_flux_type: str
    ever_fast_flux: bool
    
    # IP reuse information
    reuse_info: List[IPReuseData]


@strawberry.type
class DomainFluxLookupQuery:
    """Multi-query for domain fast flux lookup page"""
    
    @strawberry.field
    async def domain_flux_lookup(
        self,
        info: Info,
        domain_name: str
    ) -> Optional[DomainFluxLookupResult]:
        """Get comprehensive domain fast flux lookup information.

        Parameters:
            info: GraphQL resolver info
            domain_name: Domain name to look up (exact match)
        """

        # Validate domain_name input
        try:
            domain_name = InputSanitizer.sanitize_domain_search(domain_name)
        except ValueError as e:
            raise ValueError(f"Invalid domain_name: {e}")

        # ===== 1. Get Domain Info using DomainQuery =====
        domain_query = DomainQuery()
        domains = await domain_query.domains(
            info=info,
            filter=DomainFilterInput(
                domain_name=StringFilter(
                    value=domain_name,
                    operator=StringOperator.EQUALS,
                )
            ),
            limit=1,
        )

        if not domains or len(domains.items) == 0:
            return None

        domain = domains.items[0]
        domain_id = domain.id
        domain_status = domain.status

        # ===== 2. Get Fast Flux Analysis History using HistoryFastFluxQuery =====
        ff_query = HistoryFastFluxQuery()
        ff_records = await ff_query.history_fast_flux_analysis(
            info=info,
            domain_id=domain_id,
        )

        # Process fast flux data
        if ff_records:
            sorted_records = sorted(ff_records, key=lambda r: r.updated_at)
            fast_flux_first_analysis = sorted_records[0].updated_at.isoformat()
            fast_flux_last_analysis = sorted_records[-1].updated_at.isoformat()
            fast_flux_type = sorted_records[-1].flux_type.value.upper()
            ever_fast_flux = any(
                r.flux_type.value.upper() in ["SINGLE", "DOUBLE", "NAME"]
                for r in sorted_records
            )
        else:
            fast_flux_first_analysis = None
            fast_flux_last_analysis = None
            fast_flux_type = "UNKNOWN"
            ever_fast_flux = False

        # ===== 3. Get IP Connection and Reuse Info using DomainIPConnectionQuery =====
        ip_conn_query = DomainIPConnectionQuery()
        ip_connections = await ip_conn_query.domain_ip_connections(
            info=info,
            domain_id=domain_id,
        )

        ip_id_list = list(set(conn.ip_id for conn in ip_connections))

        reuse_info_result = await ip_conn_query.count_total_domain_by_ip_id(
            info=info,
            ip_id_list=ip_id_list,
            excluded_domain_id=domain_id,
        )

        return DomainFluxLookupResult(
            domain_id=domain_id,
            status=domain_status,
            fast_flux_first_analysis=fast_flux_first_analysis,
            fast_flux_last_analysis=fast_flux_last_analysis,
            fast_flux_type=fast_flux_type,
            ever_fast_flux=ever_fast_flux,
            reuse_info=reuse_info_result,
        )
    
    @strawberry.field
    async def domain_flux_history(
        self,
        info: Info,
        domain_name: str,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None
    ) -> Optional[DomainFluxHistoryResult]:
        """
        Get historical records for domain status and flux analysis
        
        Parameters:
        - domain_name: Domain name to look up
        - from_datetime: Start datetime (string in any timezone format)
        - until_datetime: End datetime (string in any timezone format)
        
        Returns historical records sorted from oldest to newest (numbered 1, 2, 3...)
        
        GraphQL Query Example:
        
        {
          domainFluxHistory(
            domainName: "example.com",
            fromDatetime: "2025-10-01T00:00:00+08:00",
            untilDatetime: "2025-10-31T23:59:59+08:00"
          ) {
            domainId
            domainStatus
            domainFlux
          }
        }
        
        Example Response:
        
        {
          "domainId": 5,
          "domainStatus": {
            "1": {"updatedAt": "2025-10-05T08:00:00+08:00", "status": "ACTIVE"},
            "2": {"updatedAt": "2025-10-15T10:00:00+08:00", "status": "SUSPENDED"},
            "3": {"updatedAt": "2025-10-20T14:00:00+08:00", "status": "ACTIVE"}
          },
          "domainFlux": {
            "1": {"updatedAt": "2025-10-06T09:00:00+08:00", "fluxType": "NONE"},
            "2": {"updatedAt": "2025-10-12T11:00:00+08:00", "fluxType": "SINGLE"},
            "3": {"updatedAt": "2025-10-18T16:00:00+08:00", "fluxType": "DOUBLE"}
          }
        }
        
        Note: Numbers (1, 2, 3...) represent chronological order from oldest to newest
        """
        # Validate domain_name input
        try:
            domain_name = InputSanitizer.sanitize_domain_search(domain_name)
        except ValueError as e:
            raise ValueError(f"Invalid domain_name: {e}")

        # ===== 1. Get Domain ID using DomainQuery =====
        domain_query = DomainQuery()
        domains = await domain_query.domains(
            info=info,
            filter=DomainFilterInput(
                domain_name=StringFilter(
                    value=domain_name,
                    operator=StringOperator.EQUALS
                )
            ),
            limit=1
        )
        
        if not domains or len(domains.items) == 0:
            return None
        
        domain_id = domains.items[0].id
        
        # ===== 2. Get History Domain Records using HistoryDomainQuery =====
        history_domain_query = HistoryDomainQuery()
        domain_status_records = await history_domain_query.history_domains(
            info=info,
            domain_id=domain_id,
            from_datetime=from_datetime,
            until_datetime=until_datetime
        )
        
        # Build domain status dict (sorted oldest to newest)
        domain_status_dict = {}
        for idx, record in enumerate(domain_status_records, start=1):
            domain_status_dict[str(idx)] = {
                "updatedAt": record.updated_at.isoformat(),
                "status": record.status.value.upper()
            }
        
        # ===== 3. Get History Fast Flux Records using HistoryFastFluxQuery =====
        history_flux_query = HistoryFastFluxQuery()
        flux_records = await history_flux_query.history_fast_flux_analysis(
            info=info,
            domain_id=domain_id,
            from_datetime=from_datetime,
            until_datetime=until_datetime
        )
        
        # Build domain flux dict (sorted oldest to newest)
        domain_flux_dict = {}
        for idx, record in enumerate(flux_records, start=1):
            domain_flux_dict[str(idx)] = {
                "updatedAt": record.updated_at.isoformat(),
                "fluxType": record.flux_type.value.upper()
            }
        
        # ===== Return Combined Result =====
        return DomainFluxHistoryResult(
            domain_id=domain_id,
            domain_status=domain_status_dict,
            domain_flux=domain_flux_dict
        )
