"""
Domain Details Summary Multi-Query
Combines data from multiple modules to provide comprehensive domain summary
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession

from ...types.dom_details.summary import DomDetailsSummary
from ...enums import FastFluxTypeEnum, DomainStatusEnum

# Import existing query classes to reuse their functions
from ...queries.domain import DomainQuery
from ...queries.fast_flux import FastFluxQuery
from ...queries.domain_ip_connection import DomainIPConnectionQuery
from ...queries.domain_ip_malicious import DomainIPMaliciousQuery
from ...queries.domain_nameserver import DomainNameserverQuery
from ...queries.nameserver_ip import NameserverIPQuery
from ...queries.source import SourceQuery


@strawberry.type
class DomDetailSummaryQuery:
    """Multi-query for domain details summary page"""

    @strawberry.field
    async def dom_details_summary(
        self,
        info: Info,
        domain_id: int
    ) -> Optional[DomDetailsSummary]:
        """
        Get comprehensive domain details summary
        
        Combines data from:
        1. Domain table - domain name, status, source, first_seen, last_seen
        2. Fast Flux Analysis - is_fast_flux, flux_type, change frequencies
        3. Domain IP Connection - total A records, domain_ip_ids
        4. Domain IP Malicious - is_malicious, malicious types, source, last updated
        5. Domain Nameserver - total NS records, nameserver IDs
        6. Nameserver IP - total NS IPs
        
        GraphQL Query Example:
        
        {
          domDetailsSummary(domainId: 5) {
            id
            domainName
            domainStatus
            sourceDomain
            isFastFlux
            fluxType
            domFirstSeen
            domLastSeen
            isMalicious
            sourceMalicious
            maliciousType
            lastMalUpdated
            totalARecords
            totalNsRecords
            totalNsIps
            aChangeFrequencyPerWeek
            nsChangeFrequencyPerWeek
          }
        }
        """
        
        # ===== 1. Get Domain Info using DomainQuery =====
        domain_query = DomainQuery()
        domain = await domain_query.domain_by_id(info=info, id=domain_id)
        
        if not domain:
            return None
        
        # Extract domain basic info
        domain_name = domain.domain_name
        domain_status = domain.status
        dom_first_seen = domain.first_seen.isoformat()
        dom_last_seen = domain.last_seen.isoformat()
        
        # Get source name from source_id
        source_query = SourceQuery()
        source = await source_query.source_by_id(info=info, id=domain.source_id)
        source_domain = source.name if source else "Unknown"
        
        # ===== 2. Get Fast Flux Analysis using FastFluxQuery =====
        ff_query = FastFluxQuery()
        ff_records = await ff_query.fast_flux_analysis(
            info=info,
            domain_id=domain_id,
            limit=100  # Get more records to check for non-UNKNOWN types
        )
        
        if ff_records:
            # Check if any record has flux_type other than UNKNOWN
            non_unknown_records = [
                r for r in ff_records 
                if r.flux_type != FastFluxTypeEnum.UNKNOWN
            ]
            
            if non_unknown_records:
                # Domain is fast flux - has at least one non-UNKNOWN record
                is_fast_flux = True
                # Use the latest non-UNKNOWN record
                latest_ff = non_unknown_records[0]
                flux_type = latest_ff.flux_type
                a_change_frequency_per_week = latest_ff.a_record_change_frequency
                ns_change_frequency_per_week = latest_ff.ns_record_change_frequency
            else:
                # All records are UNKNOWN - not fast flux
                is_fast_flux = False
                flux_type = ff_records[0].flux_type  # Use latest (which is UNKNOWN)
                a_change_frequency_per_week = ff_records[0].a_record_change_frequency
                ns_change_frequency_per_week = ff_records[0].ns_record_change_frequency
        else:
            # No records at all
            is_fast_flux = False
            flux_type = FastFluxTypeEnum.UNKNOWN
            a_change_frequency_per_week = 0
            ns_change_frequency_per_week = 0
        
        # ===== 3. Get Domain IP Connection Info using DomainIPConnectionQuery =====
        ip_conn_query = DomainIPConnectionQuery()
        
        # Get total A records
        ip_conn_info = await ip_conn_query.domain_ip_connection_info_by_id(
            info=info,
            domain_id=domain_id
        )
        total_a_records = ip_conn_info.total_ips
        
        # Get list of domain_ip_ids for malicious check
        domain_ip_ids = await ip_conn_query.get_domain_ip_ids_by_domain(
            info=info,
            domain_id=domain_id
        )
        
        # ===== 4. Get Domain IP Malicious Info using DomainIPMaliciousQuery =====
        mal_query = DomainIPMaliciousQuery()
        
        # Check if domain has any malicious records
        if domain_ip_ids:
            mal_stats = await mal_query.domain_ip_malicious_stats(
                info=info,
                domain_ip_ids=domain_ip_ids
            )
            
            is_malicious = mal_stats.total_malicious > 0
            malicious_type_list = mal_stats.list_malicious_type
            
            # Use list directly (no need to convert to dict)
            malicious_type = malicious_type_list
            
            # Get the latest malicious record for source and last_seen
            if is_malicious:
                # Get all malicious records and find the latest one
                all_mal_records = []
                for dom_ip_id in domain_ip_ids:
                    mal_records = await mal_query.domain_ip_malicious(
                        info=info,
                        domain_ip_id=dom_ip_id,
                        limit=1
                    )
                    if mal_records:
                        all_mal_records.extend(mal_records)
                
                if all_mal_records:
                    # Sort by last_seen and get the latest
                    latest_mal = max(all_mal_records, key=lambda r: r.last_seen)
                    source_malicious = latest_mal.source_name
                    last_mal_updated = latest_mal.last_seen.isoformat()
                else:
                    source_malicious = "Unknown"
                    last_mal_updated = ""
            else:
                source_malicious = ""
                last_mal_updated = ""
        else:
            is_malicious = False
            malicious_type = []
            source_malicious = ""
            last_mal_updated = ""
        
        # ===== 5. Get Domain Nameserver Info using DomainNameserverQuery =====
        ns_query = DomainNameserverQuery()
        
        # Get count and list of nameserver IDs
        ns_count_result = await ns_query.count_domain_nameservers(
            info=info,
            domain_id=domain_id
        )
        total_ns_records = ns_count_result.count
        nameserver_ids = ns_count_result.nameserver_ids
        
        # ===== 6. Get Total NS IPs using NameserverIPQuery =====
        if nameserver_ids:
            ns_ip_query = NameserverIPQuery()
            total_ns_ips = await ns_ip_query.count_ips_for_nameservers(
                info=info,
                nameserver_ids=nameserver_ids
            )
        else:
            total_ns_ips = 0
        
        # ===== Return Combined Result =====
        return DomDetailsSummary(
            id=domain_id,
            domain_name=domain_name,
            domain_status=domain_status,
            source_domain=source_domain,
            is_fast_flux=is_fast_flux,
            flux_type=flux_type,
            dom_first_seen=dom_first_seen,
            dom_last_seen=dom_last_seen,
            is_malicious=is_malicious,
            source_malicious=source_malicious,
            malicious_type=malicious_type,
            last_mal_updated=last_mal_updated,
            total_a_records=total_a_records,
            total_ns_records=total_ns_records,
            total_ns_ips=total_ns_ips,
            a_change_frequency_per_week=a_change_frequency_per_week,
            ns_change_frequency_per_week=ns_change_frequency_per_week
        )
        