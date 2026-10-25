from .domain import Domain
from .sources import Sources
from .domain_nameserver import DomainNameserver
from .nameserver import Nameserver
from .ips import IP
from .domain_ip_connection import DomainIPConnection
from .domain_ip_malicious import DomainIPMalicious
from .nameserver_ip import NameserverIP
from .fast_flux_analysis import FastFluxAnalysis
from .ip_geolocation import IPGeolocation
from .malicious_types import MaliciousType

# Historical models for time-series data
from .history_domain import HistoryDomain
from .history_ff_analysis import HistoryFastFluxAnalysis
from .history_dom_ip_conn import HistoryDomainIPConnection
from .history_dom_ns import HistoryDomainNameserver
from .history_ns_ip import HistoryNameserverIP
from .history_geoip import HistoryGeoIP
