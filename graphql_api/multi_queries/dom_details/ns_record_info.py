"""
NS Record Info Multi-Query
Combines data from multiple modules to provide comprehensive NS record information
"""
from typing import Optional
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession

from ...types.dom_details.ns_record_info import NSRecordInfo, NSToIPDetail
from ...types.domain_nameserver import DomainNameserver

# Import existing query classes to reuse their functions
from ...queries.domain_nameserver import DomainNameserverQuery
from ...queries.nameserver import NameserverQuery
from ...queries.nameserver_ip import NameserverIPQuery
from ...queries.ip import IPQuery


@strawberry.type
class NSRecordInfoQuery:
    """Multi-query for NS record information page"""

    @strawberry.field
    async def ns_record_info(
        self,
        info: Info,
        domain_id: int
    ) -> Optional[NSRecordInfo]:
        """
        Get comprehensive NS record information for a domain
        
        Combines data from:
        1. Domain Nameserver - Get all NS connections for the domain
        2. Nameserver - Get nameserver names
        3. Nameserver IP - Get IP connections for each nameserver
        4. IPs - Get IP address strings
        5. IP Geolocation - Get country and ASN/ASO info
        
        GraphQL Query Example:
        
        {
          nsRecordInfo(domainId: 5) {
            nsRecords {
              id
              nameserverId
              nameserver
              ttl
              lowestTtl
              highestTtl
              firstSeen
              lastSeen
              lowestTtlTime
            }
            nsToIpsInfo {
              ipId
              ipAddress
              nsId
              nameserver
              ipNsTtl
              ipNsLowestTtl
              firstSeen
              lastSeen
              ipNsLowestTtlTime
              country
              asnAso
            }
          }
        }
        """
        
        # ===== 1. Get List of Nameserver IDs for This Domain =====
        dom_ns_query = DomainNameserverQuery()
        
        # Get count and list of nameserver IDs
        ns_count_result = await dom_ns_query.count_domain_nameservers(
            info=info,
            domain_id=domain_id
        )
        
        nameserver_ids = ns_count_result.nameserver_ids
        
        if not nameserver_ids:
            # Return empty result if no nameservers found
            return NSRecordInfo(
                ns_records=[],
                ns_to_ips_info=[]
            )
        
        # ===== 2. Get Nameserver Details for All NS IDs =====
        ns_query = NameserverQuery()
        
        # Fetch nameservers by ID list (returns in same order as input)
        nameservers_list = await ns_query.nameserver_by_id(
            info=info,
            id_list=nameserver_ids
        )
        
        # Create a map of ns_id to nameserver name for quick lookup
        ns_name_map = {ns.id: ns.nameserver for ns in nameservers_list}
        
        # ===== 3. Build NS Records List =====
        ns_records = []
        
        for ns_id in nameserver_ids:
            # Get domain-nameserver connection info
            dom_ns_connections = await dom_ns_query.domain_nameservers(
                info=info,
                domain_id=domain_id,
                nameserver_id=ns_id,
                limit=1  # Get the latest connection
            )
            
            if not dom_ns_connections:
                continue
            
            conn = dom_ns_connections[0]
            
            # Get nameserver name from map
            nameserver_name = ns_name_map.get(ns_id, "")
            
            # Create NS record
            ns_records.append(
                DomainNameserver(
                    id=conn.id,
                    domain_id=domain_id,
                    nameserver_id=ns_id,
                    nameserver=nameserver_name,
                    first_seen=conn.first_seen,
                    last_seen=conn.last_seen,
                    ttl=conn.ttl,
                    lowest_ttl=conn.lowest_ttl,
                    lowest_ttl_time=conn.lowest_ttl_time,
                    highest_ttl=conn.highest_ttl,
                    highest_ttl_time=conn.highest_ttl_time,
                    countries=conn.countries
                )
            )
        
        # ===== 4. Build NS to IPs Info List =====
        ns_ip_query = NameserverIPQuery()
        ns_to_ips_info_list = []
        
        for ns_id in nameserver_ids:
            # Get nameserver name from map
            nameserver_name = ns_name_map.get(ns_id, "")
            
            # Get all IP connections for this nameserver
            ns_ip_connections = await ns_ip_query.nameserver_ips(
                info=info,
                nameserver_id=ns_id,
                limit=1000  # Get all connections
            )
            
            # Process each IP connection
            for conn in ns_ip_connections:
                # Extract IP address (already included in nameserver_ips result)
                ip_address = conn.ip_address or ""
                
                # Get geolocation info from the connection
                country = conn.country
                asn_aso = conn.asn_aso
                
                # Create NS to IP detail record
                ns_to_ips_info_list.append(
                    NSToIPDetail(
                        ip_id=conn.ip_id,
                        ip_address=ip_address,
                        ns_id=ns_id,
                        nameserver=nameserver_name,
                        ip_ns_ttl=conn.ttl,
                        ip_ns_lowest_ttl=conn.lowest_ttl,
                        first_seen=conn.first_seen.isoformat(),
                        last_seen=conn.last_seen.isoformat(),
                        ip_ns_lowest_ttl_time=conn.lowest_ttl_time.isoformat(),
                        country=country,
                        asn_aso=asn_aso
                    )
                )
        
        # ===== Return Combined Result =====
        return NSRecordInfo(
            ns_records=ns_records,
            ns_to_ips_info=ns_to_ips_info_list
        )
