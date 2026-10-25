
"""
NS Record Info Type for Domain Details
Type definition for detailed NS record information
"""
import strawberry
from typing import List, Optional
from ...types.domain_nameserver import DomainNameserver


@strawberry.type
class NSToIPDetail:
    """Nameserver to IP connection detail"""
    ip_id: int
    ip_address: str
    ns_id: int
    nameserver: str
    ip_ns_ttl: int  # TTL of nameserver-IP connection
    ip_ns_lowest_ttl: int
    first_seen: str
    last_seen: str
    ip_ns_lowest_ttl_time: str
    country: Optional[str]
    asn_aso: Optional[str]


@strawberry.type
class NSRecordInfo:
    """Container for all NS records of a domain"""
    ns_records: List[DomainNameserver]
    ns_to_ips_info: List[NSToIPDetail]


# {
#   nsRecordInfo(domainId: 5) {
#     nsRecords {
#       id
#       nameserverId
#       nameserver
#       ttl
#       lowestTtl
#       firstSeen
#       lastSeen
#       lowestTtlTime
#     }
#     nsToIpsInfo {
#       ipId
#       ipAddress
#       nsId 
#       nameserver
#       ipNsTtl
#       ipNsLowestTtl
#       firstSeen
#       lastSeen
#       ipNsLowestTtlTime
#       country
#       asnAso
#     }
#   }
# }

# Next additional: add IP Reuse Details