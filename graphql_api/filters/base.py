"""
Base Filter Types
Reusable filter input types for different data types
"""
from datetime import datetime
from typing import Optional
import strawberry
from ..enums import StringOperator, NumberOperator, DateOperator


@strawberry.input
class StringFilter:
    """Flexible string filtering with operators"""
    value: str
    operator: StringOperator = StringOperator.EQUALS
    case_sensitive: bool = False


@strawberry.input
class IntFilter:
    """Flexible integer filtering with operators"""
    value: Optional[int] = None
    min_value: Optional[int] = None  # For BETWEEN
    max_value: Optional[int] = None  # For BETWEEN
    operator: NumberOperator = NumberOperator.EQUALS


@strawberry.input
class DateFilter:
    """Flexible date filtering with operators"""
    value: Optional[datetime] = None
    start_date: Optional[datetime] = None  # For BETWEEN
    end_date: Optional[datetime] = None    # For BETWEEN
    operator: DateOperator = DateOperator.EQUALS
