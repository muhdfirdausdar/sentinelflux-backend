import asyncio
import os
from utils.async_log import get_logger
from dotenv import load_dotenv
from sqlalchemy import text
import json
from task import TaskInterface

logger = get_logger("routine_update")

ROUTINE_UPDATE_INTERVAL = int(os.getenv("ROUTINE_UPDATE_INTERVAL", 30))  # 30 seconds default
DEFAULT_MINUTE_OFFSET =  int(os.getenv("DEFAULT_MINUTE_OFFSET", 1))  # Default minute offset

class RoutineUpdate:
    def __init__(self, session_factory, redis_instance):
        self.session_factory = session_factory
        self.redis_instance = redis_instance

    async def run(self):
        logger.info("Starting Routine Updater...")
        while True:
            try:
                # Create a new session for TaskInterface
                async with self.session_factory() as task_session:
                    task_interface = TaskInterface(task_session, self.redis_instance)
                    # Create a separate session for process_analyzed_entries
                    async with self.session_factory() as process_session:
                        await self.process_analyzed_entries(task_interface, process_session)
            except Exception as e:
                logger.error(f"Error during routine update: {e}")
            logger.debug(f"Sleeping for {ROUTINE_UPDATE_INTERVAL} seconds...")
            await asyncio.sleep(ROUTINE_UPDATE_INTERVAL)

    async def process_analyzed_entries(self, task_interface, session):
        try:
            result = await session.execute(
                text("SELECT id, domain_name, source_domain, malicious_info, is_unrated FROM transit_domain WHERE is_analyzed = true")
            )
            rows = result.fetchall()
            if not rows:
                logger.debug("No analyzed entries in transit_domain.")
                return
            for row in rows:
                id = row[0]
                domain = row[1]
                source_domain = row[2]
                malicious_info = row[3]
                is_unrated = row[4]
                malicious_type = []
                malicious_source = []
                if malicious_info:
                    try:
                        info = malicious_info if isinstance(malicious_info, dict) else json.loads(malicious_info)
                        malicious_type = info.get("malicious_type", [])
                        malicious_source = info.get("malicious_source", [])
                    except Exception as e:
                        logger.warning(f"Failed to parse malicious_info for domain {domain}: {e}")
                addon = {
                    "malicious_type": malicious_type,
                    "malicious_source": malicious_source,
                    "source_domain": source_domain,
                }
                task_data = {
                    "domain": domain,
                    "minute_offset": DEFAULT_MINUTE_OFFSET,
                    "special_ops": "routine",
                    "priority": 40,
                    "mode": "schedule",
                    "addon": addon,
                    "is_unrated": is_unrated

                }
                result = await task_interface.create_task(**task_data)
                if result.get("success"):
                    await session.execute(
                        text("DELETE FROM transit_domain WHERE id = :id"),
                        {"id": id}
                    )
                    await session.commit()
                    logger.info(f"Task created for domain {domain}, entry deleted from transit_domain.")
                else:
                    logger.warning(f"Task creation failed for domain {domain}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error in process_analyzed_entries: {e}")

# task_data structure passed to create_task():
# {
#     "domain": str,                    # Single domain name to process
#     "minute_offset": int,             # Time offset in minutes for scheduling (default: 1)
#     "special_ops": str,               # Special operation type (e.g., "routine")
#     "priority": int,                  # Task priority level (default: 40)
#     "mode": str,                      # Execution mode: "schedule" or "immediate"
#     "addon": {                        # Additional metadata dictionary
#         "malicious_type": list,       # List of malicious types detected
#         "malicious_source": list,     # List of sources that flagged as malicious
#         "source_domain": str          # Original source domain
#     },
#     "is_unrated": bool                # Whether domain is unrated (default: False)
# }

