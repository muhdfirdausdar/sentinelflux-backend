"""
GraphQL Types Package
Type definitions for GraphQL schema
"""

# Import simple types first (no relationships)
from .source import Source
from .malicious_type import MaliciousType
from .ip_geolocation import IPGeolocation
from .fast_flux import FastFluxAnalysis

# Import connection types (junction tables)
from .domain_ip_connection import DomainIPConnection
from .domain_nameserver import DomainNameserver
from .nameserver_ip import NameserverIP
from .domain_ip_malicious import DomainIPMalicious

# Import history types
from .history_domain import HistoryDomain
from .history_fast_flux import HistoryFastFluxAnalysis
from .history_dom_ip_conn import HistoryDomainIPConnection
from .history_dom_ns import HistoryDomainNameserver
from .history_ns_ip import HistoryNameserverIP
from .history_geoip import HistoryGeoIP

# Import complex types with relationships (after their dependencies)
from .ip import IP, IPResponse
from .nameserver import Nameserver, NameserverResponse
from .domain import Domain, DomainResponse

__all__ = [
    "Domain",
    "DomainResponse",
    "Source",
    "FastFluxAnalysis",
    "IP",
    "IPResponse",
    "Nameserver",
    "NameserverResponse",
    "MaliciousType",
    "IPGeolocation",
    "DomainIPConnection",
    "DomainNameserver",
    "NameserverIP",
    "DomainIPMalicious",
    "HistoryDomain",
    "HistoryFastFluxAnalysis",
    "HistoryDomainIPConnection",
    "HistoryDomainNameserver",
    "HistoryNameserverIP",
    "HistoryGeoIP",
]
