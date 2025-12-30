"""Logger helper for Tablo integration."""
import logging
from typing import Optional

_LOGGER: Optional[logging.Logger] = None
_DEBUG_ENABLED: bool = False


def get_logger(name: str) -> logging.Logger:
    """Get logger for a module."""
    return logging.getLogger(f"custom_components.{name}")


def set_debug(enabled: bool) -> None:
    """Enable or disable debug logging."""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = enabled
    
    # Set logging level for the integration
    logger = logging.getLogger("custom_components.tablo_remote")
    if enabled:
        logger.setLevel(logging.DEBUG)
        # Also set level for child loggers and handlers
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        # Log the change if logger is already configured
        if logger.handlers:
            logger.debug("Debug logging enabled")
    else:
        logger.setLevel(logging.INFO)
        # Set handlers back to INFO level
        for handler in logger.handlers:
            handler.setLevel(logging.INFO)


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled."""
    return _DEBUG_ENABLED


def log_sensitive_data(data: dict, sensitive_keys: list = None) -> dict:
    """Create a sanitized copy of data for logging, masking sensitive keys."""
    if sensitive_keys is None:
        sensitive_keys = ["password", "access_token", "authorization", "lighthousetv_authorization", "token"]
    
    sanitized = data.copy()
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = "***REDACTED***"
        # Also check nested dicts
        for k, v in sanitized.items():
            if isinstance(v, dict):
                sanitized[k] = log_sensitive_data(v, sensitive_keys)
    
    return sanitized

