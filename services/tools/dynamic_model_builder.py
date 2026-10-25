"""
Dynamic model builder for creating Pydantic models with only requested fields.
Uses aliases from schema enums and introspects PaginationBase for field types.
"""

from typing import Dict, List, Any, Type, Optional, Union
from pydantic import BaseModel, create_model
from schemas.pagination import PaginationBase, FastFluxType
from schemas.domain import DomainStatus
from datetime import datetime


def get_pagination_field_types() -> Dict[str, Type]:
    """
    Dynamically get field types from PaginationBase model.
    This ensures we always have the correct types without hardcoding.
    """
    return PaginationBase.model_fields


def create_dynamic_pagination_model_from_cols(field_cols: List) -> Type[BaseModel]:
    """
    Create a dynamic Pydantic model that only includes the requested fields.
    Always includes 'id' field since it's mandatory for response structure.
    
    Args:
        field_cols: List of field column enums indicating what fields to include
    
    Returns:
        Type[BaseModel]: A dynamic Pydantic model class with only the requested fields
    """
    pagination_fields = get_pagination_field_types()
    required_fields = {}
    
    # Always include id field as it's mandatory for response structure
    if 'id' in pagination_fields:
        field_info = pagination_fields['id']
        field_type = field_info.annotation
        required_fields['id'] = (Optional[field_type], None)
    
    # Add requested fields only, all as optional
    for field_col in field_cols:
        # Get field alias directly from the enum
        if hasattr(field_col, 'aliases'):
            field_alias = field_col.aliases
            
            # Skip if it's already added (like id)
            if field_alias in required_fields:
                continue
            
            # Get the field type from PaginationBase
            if field_alias in pagination_fields:
                field_info = pagination_fields[field_alias]
                field_type = field_info.annotation
                
                # Make field optional with None default
                required_fields[field_alias] = (Optional[field_type], None)
    
    # Create the dynamic model
    DynamicPaginationModel = create_model(
        'DynamicPaginationModel',
        **required_fields
    )
    
    return DynamicPaginationModel


def extract_field_data(pagination_item: PaginationBase, requested_fields: List[str]) -> Dict[str, Any]:
    """
    Extract only the requested field data from a PaginationBase object.
    Handles alias mapping from field names to actual PaginationBase attributes.
    
    Args:
        pagination_item: The full PaginationBase object
        requested_fields: List of field names to extract
    
    Returns:
        Dict[str, Any]: Dictionary with only the requested field data
    """
    extracted_data = {}
    
    # Handle alias mapping for special cases where field alias != PaginationBase attribute
    field_to_attribute_mapping = {
        # No mappings needed now since PaginationBase uses flux_type directly
    }

    # Only include the specifically requested fields
    for field_name in requested_fields:
        # Check if we need to map to a different attribute name
        actual_attribute = field_to_attribute_mapping.get(field_name, field_name)
        
        if hasattr(pagination_item, actual_attribute):
            value = getattr(pagination_item, actual_attribute)
            extracted_data[field_name] = value  # Use original field name as key
        else:
            # Field not found, set to None (since all fields are optional now)
            extracted_data[field_name] = None
    
    return extracted_data


def convert_single_to_dynamic_model(
    pagination_item: PaginationBase,
    dynamic_model_class: Type[BaseModel], 
    field_names: List[str]
) -> BaseModel:
    """
    Convert a single PaginationBase object to dynamic model instance.
    
    Args:
        pagination_item: Single PaginationBase object
        dynamic_model_class: The dynamic model class to use
        field_names: List of field names to extract
    
    Returns:
        BaseModel: Dynamic model instance
    """
    # Extract only the requested field data
    field_data = extract_field_data(pagination_item, field_names)
    
    # Create dynamic model instance
    return dynamic_model_class(**field_data)


def convert_to_dynamic_model(
    pagination_data: Dict[int, Any], 
    field_cols: List,
    dynamic_model_class: Type[BaseModel]
) -> Dict[int, BaseModel]:
    """
    Convert PaginationBase objects to dynamic model instances.
    
    Args:
        pagination_data: Dict of domain_id -> PaginationBase objects
        field_cols: List of requested field columns
        dynamic_model_class: The dynamic model class to use
    
    Returns:
        Dict[int, BaseModel]: Dict of domain_id -> dynamic model instances
    """
    # Get list of requested field names from enum aliases
    requested_fields = []
    for field_col in field_cols:
        if hasattr(field_col, 'aliases'):
            requested_fields.append(field_col.aliases)
    
    converted_data = {}
    
    for domain_id, pagination_item in pagination_data.items():
        # Extract only the requested field data
        field_data = extract_field_data(pagination_item, requested_fields)
        
        # Create dynamic model instance
        try:
            dynamic_instance = dynamic_model_class(**field_data)
            converted_data[domain_id] = dynamic_instance
        except Exception as e:
            # Log error but continue processing other items
            print(f"Error creating dynamic model for domain {domain_id}: {e}")
            continue
    
    return converted_data
