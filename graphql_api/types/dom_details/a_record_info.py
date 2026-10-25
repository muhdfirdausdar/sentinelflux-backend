"""
A Record Info Type for Domain Details
Type definition for detailed A record information
"""
import strawberry
from typing import List
from ...types.domain_ip_connection import DomainIPConnection


@strawberry.type
class RelatedDomain:
    """Domain related to an IP"""
    domain_id: int
    domain_name: str
    first_seen: str
    last_seen: str
    flux_type: str
    is_malicious: bool


@strawberry.type
class RelatedNameserver:
    """Nameserver related to an IP"""
    nameserver_id: int
    nameserver_name: str
    first_seen: str
    last_seen: str
    lowest_ttl: int
    latest_ttl: int


@strawberry.type
class IPReuseDetail:
    """Detailed IP reuse information showing relationships with other domains and nameservers"""
    ip_id: int
    ip_address: str
    total_relation_with_other_domains: int
    total_relation_with_other_ns: int


@strawberry.type
class ARecordAddon:
    """Additional information for related domains and nameservers"""
    related_domain: List[RelatedDomain]
    related_nameserver: List[RelatedNameserver]


@strawberry.type
class ARecordInfo:
    """Container for all A records of a domain"""
    a_records: List[DomainIPConnection]
    ip_reuse_info: List[IPReuseDetail]


"""
GraphQL Query Example Structure:

query {
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
  
  aRecordAddon(ipId: 10) {
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

Example Response Structure:

{
  "data": {
    "aRecordInfo": {
      "aRecords": [
        {
          "id": 1,
          "ipId": 10,
          "ipAddress": "18.0.0.1",
          "ttl": 3600,
          "lowestTtl": 300,
          "highestTtl": 7200,
          "firstSeen": "2023-01-10T12:00:00Z",
          "lastSeen": "2023-06-15T12:00:00Z",
          "lowestTtlTime": "2023-02-01T12:00:00Z",
          "country": "US",
          "asnAso": "AS15169 Google LLC",
          "latitudeLongitude": "37.7510,-97.8220",
          "maliciousTypes": ["Phishing"],
          "maliciousSources": ["VirusTotal"]
        }
      ],
      "ipReuseInfo": [
        {
          "ipId": 10,
          "ipAddress": "18.0.0.1",
          "totalRelationWithOtherDomains": 5,
          "totalRelationWithOtherNs": 3
        }
      ]
    },
    "aRecordAddon": {
      "relatedDomain": [
        {
          "domainId": 12,
          "domainName": "example2.com",
          "firstSeen": "2023-02-15T10:00:00Z",
          "lastSeen": "2023-06-20T14:30:00Z",
          "fluxType": "SINGLE",
          "isMalicious": true
        }
      ],
      "relatedNameserver": [
        {
          "nameserverId": 25,
          "nameserverName": "ns1.example.com",
          "firstSeen": "2023-03-01T08:00:00Z",
          "lastSeen": "2023-06-18T16:00:00Z",
          "lowestTtl": 300,
          "latestTtl": 3600
        }
      ]
    }
  }
}
"""