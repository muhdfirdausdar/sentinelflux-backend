from pydantic import BaseModel
from typing import Dict, Optional, List, Any
from datetime import datetime
from schemas.domain import DomainStatus, DomainColumn
from schemas.domain_ip_connection import DomainIPConnectionColumn
from schemas.domain_nameserver import DomainNameserverColumn
from schemas.domain_ip_malicious import DomIPMaliciousColumn
from schemas.fast_flux_analysis import FastFluxAnalysisColumn
from schemas.sources import Sources as SourcesColumn
from enum import Enum

class FastFluxType(str, Enum):
    none = "none"
    single = "single"
    double = "double"
    name = "name"  # Fixed: Database stores "name", not "nameserver"
    unknown = "unknown"

# Filter operations manager class
class FilterOperations:
    """Manages all supported filter operations"""
    
    # Define supported operations
    EQ = "eq"      # equals
    LT = "lt"      # less than
    GT = "gt"      # greater than
    NEQ = "neq"    # not equals
    LIKE = "like"  # like with %
    
    _operations = [EQ, LT, GT, NEQ, LIKE]
    
    @classmethod
    def find_operation(cls, operation_str: str):
        """Find operation if it exists in supported operations"""
        if operation_str in cls._operations:
            return operation_str
        return None
    
    @classmethod
    def is_valid_operation(cls, operation_str: str):
        """Check if operation string is valid"""
        return cls.find_operation(operation_str) is not None
    
    @classmethod
    def get_all_operations(cls):
        """Get all supported operations"""
        return cls._operations.copy()
    
    @classmethod
    def to_domain_operation(cls, operation_str: str):
        """Map filter operation to domain service operation"""
        mapping = {
            cls.EQ: "equal",
            cls.LT: "less",
            cls.GT: "greater",
            cls.NEQ: "equal",  # Will be handled with NOT in query
            cls.LIKE: "like"
        }
        return mapping.get(operation_str)

# Column resolver classes - explicit column definitions
class FilterableColumns:
    """Manages all filterable columns - explicitly defined list"""
    
    # Explicitly define which columns support filtering
    _filterable_columns = [
        # Domain table columns
        DomainColumn.DOMAIN_NAME,
        DomainColumn.STATUS,
        DomainColumn.LAST_SEEN,
        DomainColumn.SOURCE_ID,
        DomainColumn.IS_UNRATED,
        # Domain IP Connection table columns  
        DomainIPConnectionColumn.TTL,
        DomainIPConnectionColumn.IPS_AVERAGE_TTL,
        DomainIPConnectionColumn.COUNT_IPS,
        
        # Domain Nameserver table columns
        DomainNameserverColumn.TTL,
        
        # Domain IP Malicious table columns
        DomIPMaliciousColumn.IS_MALICIOUS,

        # Fast Flux Analysis table columns
        FastFluxAnalysisColumn.FLUX_TYPE,
        
        # Sources table columns
        SourcesColumn.NAME,
    ]
    
    @classmethod
    def find_column(cls, url_param: str):
        """Find column enum object from URL parameter string using canonical values and aliases"""
        for column_enum in cls._filterable_columns:
            # Check if URL param matches the canonical value or alias
            if url_param == column_enum.value or url_param == column_enum.aliases:
                return column_enum
            
        return None
    
    @classmethod
    def is_filterable(cls, url_param: str):
        """Check if URL parameter is a valid filterable column"""
        return cls.find_column(url_param) is not None
    
    @classmethod
    def get_all_filterable(cls):
        """Get all filterable column names (for documentation/validation)"""
        all_columns = []
        
        # Add all table columns with their aliases
        for column_enum in cls._filterable_columns:
            all_columns.append(column_enum.value)
            if column_enum.aliases != column_enum.value:  # Only add if alias is different
                all_columns.append(column_enum.aliases)
        
        return list(set(all_columns))  # Remove duplicates


class SortableColumns:
    """Manages all sortable columns - explicitly defined list"""
    
    # Explicitly define which columns support sorting
    _sortable_columns = [
        # Domain table columns
        DomainColumn.ID,
        DomainColumn.DOMAIN_NAME,
        DomainColumn.FIRST_SEEN,
        DomainColumn.LAST_SEEN,
        DomainColumn.STATUS,
        DomainColumn.IS_UNRATED,

        # Domain IP Connection table columns
        DomainIPConnectionColumn.FIRST_SEEN,
        DomainIPConnectionColumn.LAST_SEEN,
        DomainIPConnectionColumn.IPS_AVERAGE_TTL,
        DomainIPConnectionColumn.COUNT_IPS,
        DomainIPConnectionColumn.LOWEST_TTL,
        DomainIPConnectionColumn.HIGHEST_TTL,
        
        # Domain Nameserver table columns  
        DomainNameserverColumn.FIRST_SEEN,
        DomainNameserverColumn.LAST_SEEN,
        DomainNameserverColumn.NS_AVERAGE_TTL,
        DomainNameserverColumn.COUNT_NS,
        DomainNameserverColumn.LOWEST_TTL,
        DomainNameserverColumn.HIGHEST_TTL,
        
        # Domain IP Malicious table columns
        DomIPMaliciousColumn.FIRST_SEEN,
        DomIPMaliciousColumn.LAST_SEEN,
        
        # Fast Flux Analysis table columns
        FastFluxAnalysisColumn.DETECTED_ON,
        FastFluxAnalysisColumn.FLUX_TYPE,
        
        # Sources table columns
        SourcesColumn.NAME,
    ]
    
    @classmethod 
    def find_column(cls, url_param: str):
        """Find column enum object from URL parameter string using canonical values and aliases"""
        for column_enum in cls._sortable_columns:
            # Check if URL param matches the canonical value or alias
            if url_param == column_enum.value or url_param == column_enum.aliases:
                return column_enum
            
        return None
    
    @classmethod
    def is_sortable(cls, url_param: str):
        """Check if URL parameter is a valid sortable column"""
        return cls.find_column(url_param) is not None
    
    @classmethod
    def get_all_sortable(cls):
        """Get all sortable column names (for documentation/validation)"""
        all_columns = []
        
        # Add all table columns with their aliases
        for column_enum in cls._sortable_columns:
            all_columns.append(column_enum.value)
            if column_enum.aliases != column_enum.value:  # Only add if alias is different
                all_columns.append(column_enum.aliases)
        
        return list(set(all_columns))  # Remove duplicates

# Field table columns manager class
class FieldTable:
    """Manages all available fields for table data display"""
    
    # Define all available fields for table display
    _available_fields = [
        DomainColumn.DOMAIN_NAME,
        DomainColumn.LAST_SEEN,
        DomainColumn.STATUS,
        DomainColumn.IS_UNRATED,
        DomIPMaliciousColumn.IS_MALICIOUS,
        SourcesColumn.NAME,
        DomainIPConnectionColumn.COUNT_IPS,
        DomainIPConnectionColumn.IPS_AVERAGE_TTL,
        DomainIPConnectionColumn.LAST_SEEN,
        DomainIPConnectionColumn.LOWEST_TTL,
        DomainIPConnectionColumn.LOWEST_TTL_TIME,
        DomainIPConnectionColumn.HIGHEST_TTL,
        DomainIPConnectionColumn.HIGHEST_TTL_TIME,
        DomainNameserverColumn.COUNT_NS,
        DomainNameserverColumn.NS_AVERAGE_TTL,
        DomainNameserverColumn.LAST_SEEN,
        DomainNameserverColumn.LOWEST_TTL,
        DomainNameserverColumn.LOWEST_TTL_TIME,
        DomainNameserverColumn.HIGHEST_TTL,
        DomainNameserverColumn.HIGHEST_TTL_TIME,
        FastFluxAnalysisColumn.FLUX_TYPE
    ]
    
    @classmethod
    def find_field(cls, field_name: str):
        """Find field enum object from URL parameter string using ONLY aliases (not canonical values)"""
        for field_enum in cls._available_fields:
            # Check if URL param matches ONLY the alias (not canonical value)
            if field_name == field_enum.aliases:
                return field_enum
        return None
    
    @classmethod
    def is_valid_field(cls, field_name: str):
        """Check if field name is valid"""
        return cls.find_field(field_name) is not None
    
    @classmethod
    def get_all_fields(cls):
        """Get all available field enum objects"""
        return cls._available_fields.copy()
    
    @classmethod
    def get_all_field_names(cls):
        """Get all available field names using ONLY aliases (for documentation/validation)"""
        all_field_names = []
        
        # Add only aliases, not canonical values
        for field_enum in cls._available_fields:
            all_field_names.append(field_enum.aliases)
        
        return sorted(list(set(all_field_names)))  # Remove duplicates and sort
    
    @classmethod
    def validate_fields(cls, fields_list: list[str]):
        """Validate a list of field names and return valid enum objects and invalid strings"""
        valid_field_enums = []
        invalid_fields = []
        
        for field in fields_list:
            field_enum = cls.find_field(field)
            if field_enum:
                valid_field_enums.append(field_enum)
            else:
                invalid_fields.append(field)
        
        return valid_field_enums, invalid_fields




class PaginationBase(BaseModel):
    id: Optional[int] = None
    domain_name: Optional[str] = None
    dom_last_seen: Optional[datetime] = None
    dom_status: Optional[DomainStatus] = None
    is_unrated: Optional[bool] = None
    is_malicious: Optional[bool] = None
    source_name: Optional[str] = None  # Changed from source_domain to source_name (alias)
    num_ips: Optional[int] = None  # Changed from count_ips to num_ips (alias)
    domip_avg_ttl: Optional[int] = None
    domip_last_seen: Optional[datetime] = None
    domip_lowest_ttl: Optional[int] = None
    domip_low_ttl_seen: Optional[datetime] = None
    domip_highest_ttl: Optional[int] = None
    domip_high_ttl_seen: Optional[datetime] = None
    num_ns: Optional[int] = None  # Changed from count_ns to num_ns (alias)
    domns_avg_ttl: Optional[int] = None
    domns_last_seen: Optional[datetime] = None
    domns_lowest_ttl: Optional[int] = None
    domns_low_ttl_seen: Optional[datetime] = None
    domns_highest_ttl: Optional[int] = None
    domns_high_ttl_seen: Optional[datetime] = None
    flux_type: Optional[FastFluxType] = None

class PageReturnData(BaseModel):
    page_data: Dict[int, PaginationBase]  # Key is id (int), value is PaginationBase
    next_cursor: Optional[str] = None


class DynamicPageReturnData(BaseModel):
    """
    Return data for pagination with dynamic fields.
    page_data is a dictionary with domain_id as keys and field data as values.
    """
    # Ordered list of items. Each item is an object that must include an `id` field
    # and the requested dynamic fields. Using a list preserves ordering when
    # serialized to JSON and consumed by JavaScript clients (object key ordering
    # can be re-ordered by JS engines for numeric keys).
    page_data: List[Any]
    data_count: int
    total_data: int  # Total count of all filtered data (without pagination limit)
    at_data: int  # Current position/offset in the dataset (1-based for frontend display)
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None  # Previous cursor for backward navigation