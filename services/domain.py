from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.domain import Domain
from schemas.domain import DomainColumn
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
from utils.async_log import get_logger
from services.tools.type_converter import safe_convert_cursor_values


logger = get_logger("services.domain")

class DomainOperation(str, Enum):
    EQUAL = "equal"
    GREATER = "greater"
    LESS = "less"
    LIKE = "like"


class DomainOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


async def get_domain_data(
    db: AsyncSession,
    list_domain: List[str] | None = None,
    list_ids: List[int] | None = None,
    requested_col: List[DomainColumn] | None = None,
) -> Dict[int, Dict[str, Any]]:
    """
    Reliable function to fetch paginated domain data.
    Returns a list of dicts with fields for PaginationBase.
    Note: Some fields (e.g., num_ips, fast_flux_type) are from other tables and will be added via joins later.
    For now, they are set to None or default values.
    """
    try:
        # Dynamic select based on requested_col
        if requested_col:
            # Always include id for the key if not already in requested_col
            select_columns = [getattr(Domain, col.value) for col in requested_col]
            if DomainColumn.ID not in requested_col:
                select_columns.insert(0, Domain.id)
        else:
            # Default columns
            select_columns = [
                Domain.id,
                Domain.domain_name,
                Domain.last_seen.label("dom_last_seen"),
                Domain.status.label("dom_status"),
                Domain.is_unrated.label("is_unrated"),  # Include is_unrated by default
            ]
        
        query = select(*select_columns)

        # If list_domain is provided, filter by domain names
        if list_domain:
            query = query.where(Domain.domain_name.in_(list_domain))
        
        # If list_ids is provided, filter by ids
        if list_ids:
            query = query.where(Domain.id.in_(list_ids))

        result = await db.execute(query)
        rows = result.all()

        # Convert to dict with id as key
        domains = {}
        for row in rows:
            domain_id = row.id
            domain_dict = {}
            if requested_col:
                for col in requested_col:
                    domain_dict[col.value] = getattr(row, col.value, None)
            else:
                domain_dict = {
                    "domain_name": row.domain_name,
                    "dom_last_seen": row.dom_last_seen,
                    "dom_status": row.dom_status,
                    "is_unrated": row.is_unrated,
                }
            domains[domain_id] = domain_dict

        return domains

    except Exception as e:
        # Log error and re-raise for reliability
        logger.error(f"Error fetching domain data: {str(e)}")
        return None

    """
    Return Structure:
    {
        domain_id_1: {
            "domain_name": "example.com",
            "status": "active",
            "last_seen": datetime(...),
            "source_id": 1,
            # ... other requested columns
        },
        domain_id_2: {
            "domain_name": "test.com", 
            "status": "inactive",
            "last_seen": datetime(...),
            "source_id": 2,
            # ... other requested columns
        }
    }
    Or None if error occurs
    """


# async def get_domain_id(
#     db: AsyncSession,
#     limit: int = 10,
#     refer: List[DomainColumn] | None = None,
#     operation: List[DomainOperation] | None = None,
#     refer_value: List[Any] | None = None,
#     after_id: int | None = None,
#     order_col: DomainColumn | None = None,
#     direction: DomainOrder = DomainOrder.ASC,
# ) -> List | None:
#     """
#     Fetch domain IDs with filtering and cursor-based pagination.
#     Supports multiple filters via lists (refer, operation, refer_value) with AND logic.
#     Each index in the lists corresponds to a filter condition.
#     """
#     try:
#         query = select(Domain.id)

#         # Add filter conditions from lists (AND logic)
#         if refer and operation and refer_value and len(refer) == len(operation) == len(refer_value):
#             for i in range(len(refer)):
#                 col = getattr(Domain, refer[i].value)
#                 op = operation[i]
#                 val = refer_value[i]
#                 if op == DomainOperation.EQUAL:
#                     condition = col == val
#                 elif op == DomainOperation.GREATER:
#                     condition = col > val
#                 elif op == DomainOperation.LESS:
#                     condition = col < val
#                 elif op == DomainOperation.LIKE:
#                     condition = col.like(val)
#                 else:
#                     continue
#                 query = query.where(condition)

#         # Cursor logic using order_col and after_id
#         if order_col and after_id is not None:
#             order_column = getattr(Domain, order_col.value)
#             # Fetch the cursor value (value of order_col for the after_id record)
#             cursor_query = select(order_column).where(Domain.id == after_id)
#             cursor_result = await db.execute(cursor_query)
#             cursor_row = cursor_result.first()
#             if cursor_row:
#                 cursor_value = cursor_row[0]
#                 if direction == DomainOrder.ASC:
#                     query = query.where(
#                         or_(
#                             order_column > cursor_value,
#                             and_(
#                                 order_column == cursor_value,
#                                 Domain.id > after_id
#                             )
#                         )
#                     )
#                 else:
#                     query = query.where(
#                         or_(
#                             order_column < cursor_value,
#                             and_(
#                                 order_column == cursor_value,
#                                 Domain.id < after_id
#                             )
#                         )
#                     )

#         # Apply ordering
#         order_expressions = []
#         if order_col:
#             order_column = getattr(Domain, order_col.value)
#             if direction == DomainOrder.DESC:
#                 order_expressions.append(order_column.desc())
#             else:
#                 order_expressions.append(order_column.asc())
#         # Always add id as secondary sort for stable pagination
#         if direction == DomainOrder.DESC:
#             order_expressions.append(Domain.id.desc())
#         else:
#             order_expressions.append(Domain.id.asc())
#         query = query.order_by(*order_expressions).limit(limit)

#         result = await db.execute(query)
#         rows = result.all()

#         return rows

#     except Exception as e:
#         # Log error and return None
#         logger.error(f"Error fetching domain id list: {str(e)}")
#         return None

    """
    Return Structure:
    [
        (domain_id_1,),
        (domain_id_2,),
        (domain_id_3,),
        ...
    ]
    Or None if error occurs
    
    Each tuple contains a single domain_id that matches the filter criteria
    and cursor pagination requirements.
    """

async def sort_domain_with_cursor_paginate(
    db: AsyncSession,
    limit: int = 10,
    sort_col: DomainColumn | None = None, # col of item cursor and sort must be same
    sort_dir: str = "asc",
    sort_cursor_value: Any | None = None, 
    after_id: int | None = None,
    filter_query = None  # Optional filter query object to integrate
) -> List[int] | None:
    

    try:
        # Start with base query - either filtered domains or all domains
        if filter_query is not None:
            # Use filter query as a subquery and join with domain table for sorting
            # Note: filter queries may return 'id' (domain table) or 'domain_id' (other tables)
            filter_subquery = filter_query.subquery()
            
            # Determine which column name to use for join
            # Check if subquery has 'id' column (domain table filter) or 'domain_id' (other table filters)
            if hasattr(filter_subquery.c, 'id'):
                # Domain table filter - use select_from with join
                query = select(Domain.id).select_from(
                    Domain.__table__.join(filter_subquery, Domain.id == filter_subquery.c.id)
                )
                logger.debug(f"Using 'id' column for filter join with select_from")
            elif hasattr(filter_subquery.c, 'domain_id'):
                # Other table filters - use select_from with join on domain_id
                query = select(Domain.id).select_from(
                    Domain.__table__.join(filter_subquery, Domain.id == filter_subquery.c.domain_id)
                )
                logger.debug(f"Using 'domain_id' column for filter join with select_from")
            else:
                logger.error(f"Filter subquery has neither 'id' nor 'domain_id' column. Available columns: {filter_subquery.c.keys()}")
                return None
            
            logger.debug(f"Filter subquery columns: {list(filter_subquery.c.keys())}")
        else:
            # No filters, query all domains
            query = select(Domain.id)

        # Apply cursor logic if sort_col and sort_cursor_value are provided
        if sort_col and sort_cursor_value is not None:
            order_column = getattr(Domain, sort_col.value)
            
            # Convert cursor values to appropriate types
            converted_cursor_value, converted_after_id, conversion_success = safe_convert_cursor_values(
                sort_cursor_value, after_id
            )
            
            if not conversion_success:
                logger.warning("Cursor value conversion failed, pagination may not work correctly")
                return None
            
            if sort_dir == "asc":
                query = query.where(
                    or_(
                        order_column > converted_cursor_value,
                        and_(
                            order_column == converted_cursor_value,
                            Domain.id > converted_after_id if converted_after_id is not None else True
                        )
                    )
                )
            else:
                query = query.where(
                    or_(
                        order_column < converted_cursor_value,
                        and_(
                            order_column == converted_cursor_value,
                            Domain.id < converted_after_id if converted_after_id is not None else True
                        )
                    )
                )

        # Apply ordering
        order_expressions = []
        if sort_col:
            order_column = getattr(Domain, sort_col.value)
            if sort_dir == "desc":
                order_expressions.append(order_column.desc())
            else:
                order_expressions.append(order_column.asc())
        # Always add id as secondary sort for stable pagination
        if sort_dir == "desc":
            order_expressions.append(Domain.id.desc())
        else:
            order_expressions.append(Domain.id.asc())
        query = query.order_by(*order_expressions).limit(limit)

        # Debug: Log the compiled SQL query
        from sqlalchemy.dialects import postgresql
        compiled_query = query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        logger.debug(f"Executing SQL query: {compiled_query}")

        result = await db.execute(query)
        rows = result.all()

        domain_ids = [row[0] for row in rows]
        logger.debug(f"Returned domain IDs: {domain_ids}")
        return domain_ids

    except Exception as e:
        # Log error and return None
        logger.error(f"Error fetching domain id list: {str(e)}")
        return None
    

    """
    Return Structure:
    [
        domain_id_1,
        domain_id_2,
        domain_id_3,
        ...
    ]
    Or None if error occurs
    
    Example:
    [
        1,
        5,
        12,
    ]
    
    Each item is a domain_id that matches the filter criteria
    and cursor pagination requirements.
    """
    


