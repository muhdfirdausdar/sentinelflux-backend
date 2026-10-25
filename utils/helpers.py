from utils.async_log import get_logger

logger = get_logger("helpers")

def convert_ip_to_str(ip_obj):
    """Convert IP object to string representation"""
    result = str(ip_obj) if ip_obj else None
    logger.debug(f"Converted IP {ip_obj} to string: {result}")
    return result


def normalize_timestamps(timestamp, last_seen):
    """Normalize timestamps by removing timezone info"""
    logger.debug(f"Normalizing timestamps: {timestamp}, {last_seen}")
    normalized_timestamp = timestamp.replace(tzinfo=None)
    normalized_last_seen = last_seen.replace(tzinfo=None)
    logger.debug(f"Normalized timestamps: {normalized_timestamp}, {normalized_last_seen}")
    return normalized_timestamp, normalized_last_seen
