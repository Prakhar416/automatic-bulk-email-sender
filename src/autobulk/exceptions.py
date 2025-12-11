"""Exception utilities for autobulk."""

import functools
import traceback
from typing import Type, Callable, Any, Optional
import logging
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutobulkError(Exception):
    """Base exception for all autobulk errors."""
    
    def __init__(
        self,
        message: str,
        cause: Optional[Exception] = None,
        context: Optional[dict] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context or {}
        self.severity = severity
        self.traceback_str = traceback.format_exc() if cause else None


class ConfigurationError(AutobulkError):
    """Raised when configuration is invalid or missing."""
    pass


class AuthenticationError(AutobulkError):
    """Raised when authentication fails."""
    pass


class EmailError(AutobulkError):
    """Base class for email-related errors."""
    pass


class TemplateError(EmailError):
    """Raised when template operations fail."""
    pass


class SchedulerError(AutobulkError):
    """Raised when scheduling operations fail."""
    pass


class DatabaseError(AutobulkError):
    """Raised when database operations fail."""
    pass


class NetworkError(AutobulkError):
    """Raised when network operations fail."""
    pass


class RateLimitError(EmailError):
    """Raised when rate limits are exceeded."""
    pass


def handle_exceptions(
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
    default_return: Any = None,
    context: Optional[dict] = None
):
    """
    Decorator to handle exceptions uniformly.
    
    Args:
        logger: Logger to use for error reporting
        reraise: Whether to re-raise the exception after logging
        default_return: Value to return if an exception occurs and reraise is False
        context: Additional context to include in the error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except AutobulkError as e:
                # Add context to the exception
                if context:
                    e.context.update(context)
                
                logger.error(
                    f"Autobulk error in {func.__name__}: {e.message}",
                    extra={
                        "exception_type": type(e).__name__,
                        "severity": e.severity.value,
                        "context": e.context,
                        "cause": str(e.cause) if e.cause else None
                    },
                    exc_info=True
                )
                
                if reraise:
                    raise
                return default_return
            
            except Exception as e:
                # Handle unexpected exceptions
                error_context = context or {}
                error_context.update({
                    "function": func.__name__,
                    "args": str(args)[:200],  # Truncate to avoid log spam
                    "kwargs": str(kwargs)[:200]
                })
                
                logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    extra={
                        "exception_type": type(e).__name__,
                        "severity": ErrorSeverity.HIGH.value,
                        "context": error_context
                    },
                    exc_info=True
                )
                
                if reraise:
                    # Wrap in AutobulkError for consistency
                    raise AutobulkError(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        cause=e,
                        context=error_context,
                        severity=ErrorSeverity.HIGH
                    )
                return default_return
        
        return wrapper
    return decorator


def with_error_context(**context):
    """
    Decorator to add context to exceptions raised by a function.
    
    Args:
        **context: Context to add to any exceptions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, AutobulkError):
                    e.context.update(context)
                else:
                    # Wrap the exception
                    e = AutobulkError(
                        f"Error in {func.__name__}: {str(e)}",
                        cause=e,
                        context=context
                    )
                raise
        
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for adding context to exceptions."""
    
    def __init__(self, **context):
        self.context = context
        self.exceptions = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, AutobulkError):
            exc_val.context.update(self.context)
        elif exc_val is not None:
            # Wrap the exception
            raise AutobulkError(
                f"Error with context {self.context}: {str(exc_val)}",
                cause=exc_val,
                context=self.context
            )


def retry_on_exception(
    exceptions: tuple = (Exception,),
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger: Optional[logging.Logger] = None
):
    """
    Decorator to retry operations on certain exceptions.
    
    Args:
        exceptions: Tuple of exceptions to retry on
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay between attempts
        logger: Logger to use for retry attempts
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {current_delay}s: {e}"
                    )
                    
                    import time
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None  # This should never be reached
        
        return wrapper
    return decorator


def format_exception_chain(exception: Exception) -> str:
    """
    Format an exception chain for logging or display.
    
    Args:
        exception: The exception to format
    
    Returns:
        Formatted exception chain as a string
    """
    lines = []
    current = exception
    
    while current:
        if isinstance(current, AutobulkError):
            lines.append(f"{type(current).__name__}: {current.message}")
            if current.context:
                lines.append(f"  Context: {current.context}")
            if current.cause:
                lines.append("  Caused by:")
                current = current.cause
            else:
                break
        else:
            lines.append(f"{type(current).__name__}: {str(current)}")
            break
    
    return "\n".join(lines)