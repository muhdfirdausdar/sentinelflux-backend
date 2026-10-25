"""
DNFlux Operations Module
Handles all communication with DNFlux VM2

Direct access to:
- dnflux_pool: Global connection pool for HTTP calls
- metadata functions: get_metrics, get_metadata_summary, clear_cache
"""

from .metadata_handler import get_metrics, get_metadata_summary, clear_cache

__all__ = ['get_metrics', 'get_metadata_summary', 'clear_cache']
