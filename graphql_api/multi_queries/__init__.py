"""
GraphQL Multi-Queries Package
Combined queries that fetch data from multiple tables/modules
"""

from .dom_flux_lookup import DomainFluxLookupQuery
from .dom_details.summary import DomDetailSummaryQuery
from .dom_details.a_record_info import ARecordInfoQuery
from .dom_details.ns_record_info import NSRecordInfoQuery
from .dom_details.visualization import VisualizationQuery

__all__ = [
    "DomainFluxLookupQuery",
    "DomDetailSummaryQuery",
    "ARecordInfoQuery",
    "NSRecordInfoQuery",
    "VisualizationQuery",
]
