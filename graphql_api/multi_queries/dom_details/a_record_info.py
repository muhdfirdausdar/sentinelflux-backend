"""
A Record Info Multi-Query
Combines data from multiple modules to provide comprehensive A record information
"""
from typing import Optional
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession

from ...types.dom_details.a_record_info import (
    ARecordInfo, IPReuseDetail, ARecordAddon, RelatedDomain, RelatedNameserver
)
from ...types.domain_ip_connection import DomainIPConnection

# Import existing query classes to reuse their functions
from ...queries.domain_ip_connection import DomainIPConnectionQuery
from ...queries.ip import IPQuery
from ...queries.nameserver_ip import NameserverIPQuery
from ...queries.domain import DomainQuery
from ...queries.fast_flux import FastFluxQuery
from ...queries.nameserver import NameserverQuery
from ...queries.domain_nameserver import DomainNameserverQuery
from ...enums import FastFluxTypeEnum


@strawberry.type
class ARecordInfoQuery:
    """Multi-query for A record information page"""

    @strawberry.field
    async def a_record_info(
        self,
        info: Info,
        domain_id: int
    ) -> Optional[ARecordInfo]:
        """
        Get comprehensive A record information for a domain
        
        Combines data from:
        1. Domain IP Connection - Get all IP connections for the domain
        2. IPs table - Get IP address strings
        3. Domain IP Connection - Count domains using each IP (excluding current domain)
        4. Nameserver IP - Count nameservers using each IP
        
        GraphQL Query Example:
        
        {
          aRecordInfo(domainId: 5) {
            aRecords {
              id
              ipId
              ipAddress
              ttl
              lowestTtl
              highestTtl
              firstSeen
              lastSeen
              lowestTtlTime
              country
              asnAso
              latitudeLongitude
              maliciousTypes
              maliciousSources
            }
            ipReuseInfo {
              ipId
              ipAddress
              totalRelationWithOtherDomains
              totalRelationWithOtherNs
            }
          }
        }
        """
        
        # ===== 1. Get Domain IP Connections using DomainIPConnectionQuery =====
        ip_conn_query = DomainIPConnectionQuery()
        
        # Get all A records (domain-IP connections) for this domain
        a_records_raw = await ip_conn_query.domain_ip_connections(
            info=info,
            domain_id=domain_id,
            limit=1000  # Get all connections
        )
        
        if not a_records_raw:
            # Return empty result if no A records found
            return ARecordInfo(
                a_records=[],
                ip_reuse_info=[]
            )
        
        # ===== 2. Extract All Data Immediately to Avoid Closed Connection Issues =====
        # Extract all data from records before any other async operations
        a_records_data = []
        unique_ip_ids = set()
        ip_address_map = {}
        
        for record in a_records_raw:
            # Extract all fields immediately into plain values
            ip_id = record.ip_id
            ip_address = record.ip_address or ""
            
            # Add to unique IPs
            unique_ip_ids.add(ip_id)
            
            # Map ip_id to ip_address
            if ip_id not in ip_address_map:
                ip_address_map[ip_id] = ip_address
            
            # Extract all fields from the record immediately
            # This prevents "result object is closed" errors
            # Access all fields to force evaluation before connection closes
            record_id = record.id
            record_domain_id = record.domain_id
            record_ip_id = record.ip_id
            record_ip_address = record.ip_address
            record_first_seen = record.first_seen
            record_last_seen = record.last_seen
            record_ttl = record.ttl
            record_lowest_ttl = record.lowest_ttl
            record_lowest_ttl_time = record.lowest_ttl_time
            record_highest_ttl = record.highest_ttl
            record_highest_ttl_time = record.highest_ttl_time
            record_malicious_types = list(record.malicious_types) if record.malicious_types else []
            record_malicious_sources = list(record.malicious_sources) if record.malicious_sources else []
            record_country = record.country
            record_asn_aso = record.asn_aso
            record_latitude_longitude = record.latitude_longitude
            
            a_records_data.append(
                DomainIPConnection(
                    id=record_id,
                    domain_id=record_domain_id,
                    ip_id=record_ip_id,
                    ip_address=record_ip_address,
                    first_seen=record_first_seen,
                    last_seen=record_last_seen,
                    ttl=record_ttl,
                    lowest_ttl=record_lowest_ttl,
                    lowest_ttl_time=record_lowest_ttl_time,
                    highest_ttl=record_highest_ttl,
                    highest_ttl_time=record_highest_ttl_time,
                    malicious_types=record_malicious_types,
                    malicious_sources=record_malicious_sources,
                    country=record_country,
                    asn_aso=record_asn_aso,
                    latitude_longitude=record_latitude_longitude
                )
            )
        
        # Convert set to list
        unique_ip_ids = list(unique_ip_ids)
        
        # ===== 3. Get IP Reuse Statistics for All IPs =====
        # Count domains using each IP (excluding current domain)
        domain_reuse_results = await ip_conn_query.count_total_domain_by_ip_id(
            info=info,
            ip_id_list=unique_ip_ids,
            excluded_domain_id=domain_id
        )
        
        # Create a map of ip_id to domain reuse count
        domain_reuse_map = {
            result.ip_id: result.total_domain_reused 
            for result in domain_reuse_results
        }
        
        # ===== 4. Count Nameservers for Each IP =====
        ns_ip_query = NameserverIPQuery()
        
        ip_reuse_info_list = []
        for ip_id in unique_ip_ids:
            # Get IP address from map
            ip_address = ip_address_map.get(ip_id, "")
            
            # Get domain reuse count from map
            total_relation_with_other_domains = domain_reuse_map.get(ip_id, 0)
            
            # Count nameservers using this IP
            ns_count_result = await ns_ip_query.count_nameservers_by_ip(
                info=info,
                ip_id=ip_id
            )
            total_relation_with_other_ns = ns_count_result.total_ns_id
            
            # Add to reuse info list
            ip_reuse_info_list.append(
                IPReuseDetail(
                    ip_id=ip_id,
                    ip_address=ip_address,
                    total_relation_with_other_domains=total_relation_with_other_domains,
                    total_relation_with_other_ns=total_relation_with_other_ns
                )
            )
        
        # ===== Return Combined Result =====
        return ARecordInfo(
            a_records=a_records_data,
            ip_reuse_info=ip_reuse_info_list
        )
    
    @strawberry.field
    async def a_record_addon(
        self,
        info: Info,
        ip_id: int,
        domain_id: int
    ) -> Optional[ARecordAddon]:
        """
        Get additional information about related domains and nameservers for a specific IP
        
        Combines data from:
        1. Domain IP Connection - Get list of domains using this IP
        2. Nameserver IP - Get list of nameservers using this IP
        3. Domain - Get domain details
        4. Fast Flux - Get flux type for each domain
        5. Domain IP Malicious - Check if domain is malicious
        6. Nameserver - Get nameserver details
        7. Domain Nameserver - Get nameserver connection details
        
        GraphQL Query Example:
        
        {
          aRecordAddon(ipId: 10, domainId: 5) {
            relatedDomain {
              domainId
              domainName
              firstSeen
              lastSeen
              fluxType
              isMalicious
            }
            relatedNameserver {
              nameserverId
              nameserverName
              firstSeen
              lastSeen
              lowestTtl
              latestTtl
            }
          }
        }
        """
        
        # ===== 1. Get List of Domain IDs Using This IP =====
        ip_conn_query = DomainIPConnectionQuery()
        
        # Count and get list of domains using this IP (excluding the current domain)
        domain_reuse_result = await ip_conn_query.count_total_domain_by_ip_id(
            info=info,
            ip_id_list=[ip_id],
            excluded_domain_id=domain_id
        )
        
        # Extract list of domain IDs
        domain_ids = domain_reuse_result[0].list_domain if domain_reuse_result else []
        
        # ===== 2. Get List of Nameserver IDs Using This IP =====
        ns_ip_query = NameserverIPQuery()
        
        # Count and get list of nameservers using this IP
        ns_count_result = await ns_ip_query.count_nameservers_by_ip(
            info=info,
            ip_id=ip_id
        )
        
        # Extract list of nameserver IDs
        nameserver_ids = ns_count_result.list_ns_id
        
        # ===== 3. Fetch Related Domain Information =====
        related_domains = []
        domain_query = DomainQuery()
        ff_query = FastFluxQuery()
        
        for dom_id in domain_ids:
            # Get domain details
            domain = await domain_query.domain_by_id(info=info, id=dom_id)
            
            if not domain:
                continue
            
            # Extract domain name, first_seen, last_seen
            domain_name = domain.domain_name
            first_seen = domain.first_seen.isoformat()
            last_seen = domain.last_seen.isoformat()
            
            # Get flux type from fast flux analysis
            ff_records = await ff_query.fast_flux_analysis(
                info=info,
                domain_id=dom_id,
                limit=1  # Get latest only
            )
            
            if ff_records:
                flux_type = ff_records[0].flux_type.value.upper()
            else:
                flux_type = "UNKNOWN"
            
            # Check if domain is malicious
            # Get domain-IP connections for this domain
            connections = await ip_conn_query.domain_ip_connections(
                info=info,
                domain_id=dom_id,
                ip_id=ip_id,
                limit=1
            )
            
            is_malicious = False
            if connections:
                malicious_types = connections[0].malicious_types
                # Check if malicious_types is not empty and doesn't contain only "unknown"
                if malicious_types:
                    # Filter out "unknown" (case insensitive)
                    non_unknown_types = [
                        m for m in malicious_types 
                        if m.lower() not in ["unknown", "null", ""]
                    ]
                    is_malicious = len(non_unknown_types) > 0
            
            # Add to related domains list
            related_domains.append(
                RelatedDomain(
                    domain_id=dom_id,
                    domain_name=domain_name,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    flux_type=flux_type,
                    is_malicious=is_malicious
                )
            )
        
        # ===== 4. Fetch Related Nameserver Information =====
        related_nameservers = []
        ns_query = NameserverQuery()
        dom_ns_query = DomainNameserverQuery()
        
        for ns_id in nameserver_ids:
            # Get nameserver name
            nameservers = await ns_query.nameserver_by_id(info=info, id_list=[ns_id])
            
            if not nameservers:
                continue
            
            nameserver_name = nameservers[0].nameserver
            
            # Get nameserver-IP connection details from domain_nameserver
            # Note: We need to find which domain this nameserver is connected to
            # For now, we'll use the nameserver-IP connection details
            ns_ip_connections = await ns_ip_query.nameserver_ips(
                info=info,
                nameserver_id=ns_id,
                ip_id=ip_id,
                limit=1
            )
            
            if ns_ip_connections:
                conn = ns_ip_connections[0]
                first_seen = conn.first_seen.isoformat()
                last_seen = conn.last_seen.isoformat()
                lowest_ttl = conn.lowest_ttl
                latest_ttl = conn.ttl
            else:
                # Default values if no connection found
                first_seen = ""
                last_seen = ""
                lowest_ttl = 0
                latest_ttl = 0
            
            # Add to related nameservers list
            related_nameservers.append(
                RelatedNameserver(
                    nameserver_id=ns_id,
                    nameserver_name=nameserver_name,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    lowest_ttl=lowest_ttl,
                    latest_ttl=latest_ttl
                )
            )
        
        # ===== Return Combined Result =====
        return ARecordAddon(
            related_domain=related_domains,
            related_nameserver=related_nameservers
        )
