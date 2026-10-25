import logging
import logging.handlers
import os
import sys
import json
from dotenv import load_dotenv

try:
    from colorlog import ColoredFormatter
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False
    # Fallback to regular formatter
    ColoredFormatter = logging.Formatter

load_dotenv()

LOG_COUNT = int(os.getenv("LOG_COUNT", 3))
LOG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
DEBUG_ON = str(os.getenv("DEBUG", "false")).lower() in ("1", "true", "yes")
FULL_DEBUG = str(os.getenv("FULL_DEBUG", "false")).lower() in ("1", "true", "yes")

# Convert env strings to bool
def str_to_bool(val):
    return str(val).lower() in ("1", "true", "yes")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "level": record.levelname,
            "time": self.formatTime(record, self.datefmt),
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
        }
        return json.dumps(log_record)

def get_logger(name: str = "sentinelflux", json_logs: bool = None):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    # Load from .env or override with argument
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    console_log_level = os.getenv("CONSOLE_LOG_LEVEL", log_level).upper()
    file_log_level = os.getenv("FILE_LOG_LEVEL", log_level).upper()
    
    json_file = str_to_bool(os.getenv("LOG_JSON_FILE", "false"))
    json_console = str_to_bool(os.getenv("LOG_JSON_CONSOLE", "false"))

    # Set logger level: only allow DEBUG if FULL_DEBUG is True
    if FULL_DEBUG:
        level = logging.DEBUG
    else:
        level = logging.INFO

    console_level = getattr(logging, console_log_level, logging.INFO)
    file_level = getattr(logging, file_log_level, logging.INFO)

    # Set handler levels based on FULL_DEBUG and DEBUG_ON
    if FULL_DEBUG:
        file_level = logging.DEBUG
        if DEBUG_ON:
            console_level = logging.DEBUG
    else:
        file_level = getattr(logging, file_log_level, logging.INFO)
        if DEBUG_ON:
            console_level = getattr(logging, console_log_level, logging.INFO)

    logger.setLevel(level)

    # Handlers
    log_dir = LOG_FOLDER
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")
    error_warn_file = os.path.join(log_dir, "errors_warnings.log")

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=LOG_COUNT
    )
    file_handler.setLevel(file_level)

    # Handler for warnings and errors only
    error_warn_handler = logging.handlers.RotatingFileHandler(
        error_warn_file, maxBytes=5 * 1024 * 1024, backupCount=LOG_COUNT
    )
    error_warn_handler.setLevel(logging.WARNING)

    # Only add console handler if DEBUG_ON is True
    if DEBUG_ON:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
    else:
        console_handler = None

    # Formatters
    if json_file:
        file_handler.setFormatter(JsonFormatter())
        error_warn_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        error_warn_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    if console_handler:
        if json_console:
            console_handler.setFormatter(JsonFormatter())
        else:
            if HAS_COLORLOG:
                console_handler.setFormatter(ColoredFormatter(
                    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "bold_red",
                    },
                ))
            else:
                console_handler.setFormatter(logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ))

    logger.addHandler(file_handler)
    logger.addHandler(error_warn_handler)
    if console_handler:
        logger.addHandler(console_handler)

    # Prevent duplicate logs by disabling propagation to root logger
    logger.propagate = False

    return logger
