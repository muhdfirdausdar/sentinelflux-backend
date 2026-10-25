from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.sources import Sources
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
from utils.async_log import get_logger

logger = get_logger("services.sources")

async def get_source_name(db : AsyncSession, source_id: int | List[int] | None = None) -> str | Dict[int, str] | None:
    """
    Fetch source name(s) given source_id(s).
    Can handle single source_id or list of source_ids for batch processing.

    Args:
        source_id: Single source_id (int) or list of source_ids (List[int])

    Returns:
        - If single source_id: source_name (str) or None
        - If list of source_ids: dict {source_id: source_name} or None
    """
    try:
        if source_id is None:
            return None

        # Handle single source_id
        if isinstance(source_id, int):
            query = select(Sources.id, Sources.name).where(Sources.id == source_id)
            result = await db.execute(query)
            row = result.first()
            if row:
                return row[1]  # source_name
            return None

        # Handle list of source_ids
        elif isinstance(source_id, list):
            if not source_id:
                return {}

            query = select(Sources.id, Sources.name).where(Sources.id.in_(source_id))
            result = await db.execute(query)
            rows = result.all()

            # Build dictionary mapping source_id to source_name
            source_names = {}
            for row in rows:
                source_names[row[0]] = row[1]  # {source_id: source_name}

            return source_names

        else:
            logger.error(f"Invalid source_id type: {type(source_id)}")
            return None

    except Exception as e:
        logger.error(f"Error fetching source name(s) for source_id {source_id}: {e}")
        return None
