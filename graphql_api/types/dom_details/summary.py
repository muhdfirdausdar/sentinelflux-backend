"""
Domain Details Summary Type
Type definition for domain details summary page

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

Response Example:

{
  "domDetailsSummary": {
    "id": 5,
    "domainName": "example.com",
    "domainStatus": "ACTIVE",
    "sourceDomain": "VirusTotal",
    "isFastFlux": true,
    "fluxType": "SINGLE_FLUX",
    "domFirstSeen": "2025-10-01T10:00:00",
    "domLastSeen": "2025-11-14T15:30:00",
    "isMalicious": true,
    "sourceMalicious": "VirusTotal",
    "maliciousType": ["Phishing", "Malware"],
    "lastMalUpdated": "2025-11-14T14:00:00",
    "totalARecords": 25,
    "totalNsRecords": 4,
    "totalNsIps": 8,
    "aChangeFrequencyPerWeek": 12,
    "nsChangeFrequencyPerWeek": 2
  }
}
"""
import strawberry
from typing import List
from ...enums import FastFluxTypeEnum, DomainStatusEnum


@strawberry.type
class DomDetailsSummary:
    id: int
    domain_name: str # use domain module -> domain name
    domain_status: DomainStatusEnum # use domain module -> status
    source_domain: str # use domain module -> source
    is_fast_flux: bool # use fast flux module -> if there is any record for the domain id that not UNKNOWN
    flux_type: FastFluxTypeEnum # use fast flux module -> get the latest flux type for the domain id
    dom_first_seen: str # use domain module -> first_seen
    dom_last_seen: str # use domain module -> last_seen
    is_malicious: bool # use domain ip malicious -> if there is any record for the domain id
    source_malicious: str # use domain ip malicious -> get source name of the latest malicious record
    malicious_type: List[str]  # List of malicious type names
    last_mal_updated: str # use domain_ip_malicious -> last_seen
    total_a_records: int # domain_ip_connection -> totalIps
    total_ns_records: int # domain_nameserver -> use count ns by domain id
    total_ns_ips: int  # using same operation of total NS records, get list of ns id, then use domain_nameserver to count ns ip
    a_change_frequency_per_week: int # From fast flux -> aRecordChangeFrequency
    ns_change_frequency_per_week: int # From fast flux -> nsRecordChangeFrequency
