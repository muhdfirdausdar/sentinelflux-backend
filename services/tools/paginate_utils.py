"""
Pagination Utilities Module

This module contains utility functions for handling pagination-related operations,
including filter and sort column categorization across different database tables.
"""

from typing import List, Dict, Any, Tuple, Optional
from schemas.domain import DomainColumn
from schemas.domain_ip_connection import DomainIPConnectionColumn
from schemas.domain_nameserver import DomainNameserverColumn
from schemas.sources import Sources as SourcesColumn
from schemas.fast_flux_analysis import FastFluxAnalysisColumn
from schemas.domain_ip_malicious import DomIPMaliciousColumn


def categorize_filters_and_sort(
    filter_col: List[str] | None = None,
    filter_ops: List[str] | None = None,
    filter_val: List[Any] | None = None,
    sort_col: str | None = None
) -> Dict[str, Any]:
    """
    Categorize filters and sort columns by their respective database tables.

    Args:
        filter_col: List of filter column names (URL parameter format)
        filter_ops: List of filter operations
        filter_val: List of filter values
        sort_col: Sort column name (URL parameter format)

    Returns:
        Dict containing categorized filters and sort information:
        {
            'domain_filters': {'cols': [], 'ops': [], 'vals': []},
            'ip_conn_filters': {'cols': [], 'ops': [], 'vals': []},
            'ns_conn_filters': {'cols': [], 'ops': [], 'vals': []},
            'sources_filters': {'cols': [], 'ops': [], 'vals': []},
            'ff_analysis_filters': {'cols': [], 'ops': [], 'vals': []},
            'dom_ip_mal_filters': {'cols': [], 'ops': [], 'vals': []},
            'sort_table': str | None,
            'sort_column_enum': Enum | None
        }
    """

    # Initialize filter groups for each table
    result = {
        'domain_filters': {'cols': [], 'ops': [], 'vals': []},
        'ip_conn_filters': {'cols': [], 'ops': [], 'vals': []},
        'ns_conn_filters': {'cols': [], 'ops': [], 'vals': []},
        'sources_filters': {'cols': [], 'ops': [], 'vals': []},
        'ff_analysis_filters': {'cols': [], 'ops': [], 'vals': []},
        'dom_ip_mal_filters': {'cols': [], 'ops': [], 'vals': []},
        'sort_table': None,
        'sort_column_enum': None
    }

    # Step 1: Group filters by table using .table property
    if filter_col and filter_ops and filter_val:
        for i, col_name in enumerate(filter_col):
            if i < len(filter_ops) and i < len(filter_val):
                # Find the column enum from any table
                column_enum = None
                table_name = None

                # Check each table's column enum
                column_enum = DomainColumn.from_alias(col_name)
                if column_enum:
                    table_name = column_enum.table
                else:
                    column_enum = DomainIPConnectionColumn.from_alias(col_name)
                    if column_enum:
                        table_name = column_enum.table
                    else:
                        column_enum = DomainNameserverColumn.from_alias(col_name)
                        if column_enum:
                            table_name = column_enum.table
                        else:
                            column_enum = SourcesColumn.from_alias(col_name)
                            if column_enum:
                                table_name = column_enum.table
                            else:
                                column_enum = FastFluxAnalysisColumn.from_alias(col_name)
                                if column_enum:
                                    table_name = column_enum.table
                                else:
                                    column_enum = DomIPMaliciousColumn.from_alias(col_name)
                                    if column_enum:
                                        table_name = column_enum.table

                # Add to appropriate filter group
                if table_name == "domain":
                    result['domain_filters']['cols'].append(column_enum)
                    result['domain_filters']['ops'].append(filter_ops[i])
                    result['domain_filters']['vals'].append(filter_val[i])
                elif table_name == "domain_ip_connection":
                    result['ip_conn_filters']['cols'].append(column_enum)
                    result['ip_conn_filters']['ops'].append(filter_ops[i])
                    result['ip_conn_filters']['vals'].append(filter_val[i])
                elif table_name == "domain_nameserver":
                    result['ns_conn_filters']['cols'].append(column_enum)
                    result['ns_conn_filters']['ops'].append(filter_ops[i])
                    result['ns_conn_filters']['vals'].append(filter_val[i])
                elif table_name == "sources":
                    result['sources_filters']['cols'].append(column_enum)
                    result['sources_filters']['ops'].append(filter_ops[i])
                    result['sources_filters']['vals'].append(filter_val[i])
                elif table_name == "fast_flux_analysis":
                    result['ff_analysis_filters']['cols'].append(column_enum)
                    result['ff_analysis_filters']['ops'].append(filter_ops[i])
                    result['ff_analysis_filters']['vals'].append(filter_val[i])
                elif table_name == "domain_ip_malicious":
                    result['dom_ip_mal_filters']['cols'].append(column_enum)
                    result['dom_ip_mal_filters']['ops'].append(filter_ops[i])
                    result['dom_ip_mal_filters']['vals'].append(filter_val[i])

    # Step 2: Categorize the sort_col based on table
    if sort_col:
        # Find which table the sort column belongs to
        sort_column_enum = DomainColumn.from_alias(sort_col)
        if sort_column_enum:
            result['sort_table'] = sort_column_enum.table
            result['sort_column_enum'] = sort_column_enum
        else:
            sort_column_enum = DomainIPConnectionColumn.from_alias(sort_col)
            if sort_column_enum:
                result['sort_table'] = sort_column_enum.table
                result['sort_column_enum'] = sort_column_enum
            else:
                sort_column_enum = DomainNameserverColumn.from_alias(sort_col)
                if sort_column_enum:
                    result['sort_table'] = sort_column_enum.table
                    result['sort_column_enum'] = sort_column_enum
                else:
                    sort_column_enum = SourcesColumn.from_alias(sort_col)
                    if sort_column_enum:
                        result['sort_table'] = sort_column_enum.table
                        result['sort_column_enum'] = sort_column_enum
                    else:
                        sort_column_enum = FastFluxAnalysisColumn.from_alias(sort_col)
                        if sort_column_enum:
                            result['sort_table'] = sort_column_enum.table
                            result['sort_column_enum'] = sort_column_enum
                        else:
                            sort_column_enum = DomIPMaliciousColumn.from_alias(sort_col)
                            if sort_column_enum:
                                result['sort_table'] = sort_column_enum.table
                                result['sort_column_enum'] = sort_column_enum

    return result


def get_filter_summary(categorized_data: Dict[str, Any]) -> str:
    """
    Generate a summary string of the categorized filters for debugging.

    Args:
        categorized_data: Result from categorize_filters_and_sort()

    Returns:
        Summary string showing filter counts by table
    """
    summary_parts = []

    # Count filters for each table
    for table_key, filter_data in categorized_data.items():
        if table_key.endswith('_filters'):
            count = len(filter_data['cols'])
            table_name = table_key.replace('_filters', '').replace('_', ' ').title()
            if count > 0:
                summary_parts.append(f"{table_name}: {count}")

    if summary_parts:
        return f"Filter groups - {', '.join(summary_parts)}"
    else:
        return "Filter groups - None"


def get_sort_summary(categorized_data: Dict[str, Any]) -> str:
    """
    Generate a summary string of the sort column categorization for debugging.

    Args:
        categorized_data: Result from categorize_filters_and_sort()

    Returns:
        Summary string showing sort column information
    """
    sort_table = categorized_data.get('sort_table')
    sort_column_enum = categorized_data.get('sort_column_enum')

    if sort_table and sort_column_enum:
        return f"Sort column: {sort_column_enum.value}, Table: {sort_table}, Enum: {sort_column_enum}"
    else:
        return "Sort column: None"
