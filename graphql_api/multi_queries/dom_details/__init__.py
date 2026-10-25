"""
Domain Details Multi-Queries Package
Combined queries for domain details pages
"""

from .summary import DomDetailSummaryQuery
from .a_record_info import ARecordInfoQuery
from .ns_record_info import NSRecordInfoQuery
from .visualization import VisualizationQuery

__all__ = [
    "DomDetailSummaryQuery",
    "ARecordInfoQuery",
    "NSRecordInfoQuery",
    "VisualizationQuery",
]
