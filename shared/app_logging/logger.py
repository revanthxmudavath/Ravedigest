"""
Standardized logging utilities for RaveDigest services.
Provides structured logging with correlation IDs and consistent formatting.
"""

import logging
import json
import uuid
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime
from shared.config.settings import get_settings

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIDFilter(logging.Filter):
    """Logging filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "no-correlation-id"
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'no-correlation-id'),
            "service": getattr(record, 'service_name', 'unknown'),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info', 'correlation_id']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class StructuredFormatter(logging.Formatter):
    """Structured formatter for human-readable logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        correlation_id = getattr(record, 'correlation_id', 'no-correlation-id')
        service = getattr(record, 'service_name', 'unknown')
        
        # Format: [timestamp] [level] [service] [correlation_id] logger: message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        base_msg = f"[{timestamp}] [{record.levelname}] [{service}] [{correlation_id}] {record.name}: {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
        
        return base_msg


def setup_logging(
    service_name: str,
    log_level: Optional[str] = None,
    json_logs: Optional[bool] = None,
    include_correlation_id: Optional[bool] = None
) -> logging.Logger:
    """
    Set up standardized logging for a service.
    
    Args:
        service_name: Name of the service (e.g., 'collector', 'analyzer')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to use JSON formatting
        include_correlation_id: Whether to include correlation IDs
    
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Use provided values or fall back to settings
    level = log_level or settings.logging.level
    use_json = json_logs if json_logs is not None else settings.logging.json_logs
    include_corr_id = include_correlation_id if include_correlation_id is not None else settings.logging.include_correlation_id
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, level.upper()))
    
    # Set formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = StructuredFormatter()
    
    handler.setFormatter(formatter)
    
    # Add correlation ID filter if enabled
    if include_corr_id:
        handler.addFilter(CorrelationIDFilter())
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Add service name to all log records
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.service_name = service_name
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    return logger


def get_logger(service_name: str) -> logging.Logger:
    """Get a logger for a specific service."""
    return logging.getLogger(service_name)


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def log_function_call(logger: logging.Logger, func_name: str, **kwargs) -> None:
    """Log a function call with parameters."""
    logger.debug(f"Calling {func_name}", extra={"function": func_name, "parameters": kwargs})


def log_function_result(logger: logging.Logger, func_name: str, result: Any = None, **kwargs) -> None:
    """Log a function result."""
    extra = {"function": func_name, "result": result}
    extra.update(kwargs)
    logger.debug(f"Function {func_name} completed", extra=extra)


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any]) -> None:
    """Log an error with additional context."""
    logger.error(
        f"Error occurred: {str(error)}",
        extra={"error_type": type(error).__name__, "context": context},
        exc_info=True
    )


# Context manager for correlation IDs
class CorrelationContext:
    """Context manager for setting correlation IDs."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.old_correlation_id: Optional[str] = None
    
    def __enter__(self) -> str:
        self.old_correlation_id = get_correlation_id()
        set_correlation_id(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_correlation_id:
            set_correlation_id(self.old_correlation_id)
        else:
            correlation_id_var.set(None)
