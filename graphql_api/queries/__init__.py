"""
GraphQL Queries Package
Query resolvers for different entities
"""

from .domain import DomainQuery
from .source import SourceQuery
from .fast_flux import FastFluxQuery
from .ip import IPQuery
from .nameserver import NameserverQuery
from .malicious_type import MaliciousTypeQuery
from .ip_geolocation import IPGeolocationQuery
from .domain_ip_connection import DomainIPConnectionQuery
from .domain_nameserver import DomainNameserverQuery
from .nameserver_ip import NameserverIPQuery
from .domain_ip_malicious import DomainIPMaliciousQuery
from .history_domain import HistoryDomainQuery
from .history_fast_flux import HistoryFastFluxQuery
from .history_dom_ip_conn import HistoryDomainIPConnectionQuery
from .history_dom_ns import HistoryDomainNameserverQuery
from .history_ns_ip import HistoryNameserverIPQuery
from .history_geoip import HistoryGeoIPQuery

__all__ = [
    "DomainQuery",
    "SourceQuery",
    "FastFluxQuery",
    "IPQuery",
    "NameserverQuery",
    "MaliciousTypeQuery",
    "IPGeolocationQuery",
    "DomainIPConnectionQuery",
    "DomainNameserverQuery",
    "NameserverIPQuery",
    "DomainIPMaliciousQuery",
    "HistoryDomainQuery",
    "HistoryFastFluxQuery",
    "HistoryDomainIPConnectionQuery",
    "HistoryDomainNameserverQuery",
    "HistoryNameserverIPQuery",
    "HistoryGeoIPQuery",
]
