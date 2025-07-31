import structlog
import logging
import sys
import orjson as json
from pathlib import Path
from src.config.settings import settings


def chinese_friendly_json_renderer(_, __, event_dict):
    """Custom JSON renderer that preserves Chinese characters."""
    return json.dumps(
        event_dict,
        option=json.OPT_INDENT_2  # 格式化输出，orjson默认不转义非ASCII字符
    ).decode()


def configure_logging():
    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.log_file_path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure standard logging with both console and file output
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            chinese_friendly_json_renderer
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )