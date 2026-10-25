"""
GraphQL Enums
Shared enumerations used across the GraphQL schema
"""
from enum import Enum
import strawberry


@strawberry.enum
class DomainStatusEnum(Enum):
    """Domain status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


@strawberry.enum
class FastFluxTypeEnum(Enum):
    """Fast flux type enumeration"""
    SINGLE = "single"
    DOUBLE = "double"
    NAME = "name"
    UNKNOWN = "unknown"


@strawberry.enum
class SortOrder(Enum):
    """Sort order for queries"""
    ASC = "asc"
    DESC = "desc"


@strawberry.enum
class StringOperator(Enum):
    """String comparison operators"""
    EQUALS = "eq"              # Exact match
    NOT_EQUALS = "ne"          # Not equal
    CONTAINS = "contains"      # LIKE %value%
    STARTS_WITH = "starts"     # LIKE value%
    ENDS_WITH = "ends"         # LIKE %value
    IN = "in"                  # IN (value1, value2, ...)
    NOT_IN = "not_in"          # NOT IN (...)


@strawberry.enum
class NumberOperator(Enum):
    """Numeric comparison operators"""
    EQUALS = "eq"              # =
    NOT_EQUALS = "ne"          # !=
    GREATER_THAN = "gt"        # >
    GREATER_THAN_OR_EQUAL = "gte"  # >=
    LESS_THAN = "lt"           # <
    LESS_THAN_OR_EQUAL = "lte"     # <=
    BETWEEN = "between"        # BETWEEN min AND max


@strawberry.enum
class DateOperator(Enum):
    """Date comparison operators"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    AFTER = "after"            # >
    AFTER_OR_ON = "after_or_on"    # >=
    BEFORE = "before"          # <
    BEFORE_OR_ON = "before_or_on"  # <=
    BETWEEN = "between"
