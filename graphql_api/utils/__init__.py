"""
GraphQL Utils Package
"""

from .db_helpers import (
    # Source helpers
    get_source_by_id,
    get_source_by_name,
    get_all_sources,
    
    # Domain helpers
    get_domain_by_id,
    get_domain_by_name,
    get_domains_by_source,
    get_domains_by_status,
    count_domains_by_source,
    count_domains_by_status,
    
    # Fast Flux helpers
    get_fast_flux_by_id,
    get_fast_flux_by_domain,
    count_fast_flux_by_domain,
    count_fast_flux_by_type,
    
    # Cross-table helpers
    get_domains_with_flux_type,
    get_domains_with_source_and_flux,
    count_domains_with_flux,
)

from .datetime_utils import (
    parse_datetime_with_timezone,
    normalize_to_utc,
    normalize_to_utc8,
    convert_datetime_to_timezone,
    get_current_utc,
    get_current_utc8,
    DB_TIMEZONE,
    DB_TIMEZONE_NAME,
)

__all__ = [
    "get_source_by_id",
    "get_source_by_name",
    "get_all_sources",
    "get_domain_by_id",
    "get_domain_by_name",
    "get_domains_by_source",
    "get_domains_by_status",
    "count_domains_by_source",
    "count_domains_by_status",
    "get_fast_flux_by_id",
    "get_fast_flux_by_domain",
    "count_fast_flux_by_domain",
    "count_fast_flux_by_type",
    "get_domains_with_flux_type",
    "get_domains_with_source_and_flux",
    "count_domains_with_flux",
    "parse_datetime_with_timezone",
    "normalize_to_utc",
    "normalize_to_utc8",
    "convert_datetime_to_timezone",
    "get_current_utc",
    "get_current_utc8",
    "DB_TIMEZONE",
    "DB_TIMEZONE_NAME",
]
