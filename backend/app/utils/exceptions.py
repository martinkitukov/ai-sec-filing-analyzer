"""
Custom exceptions for AI SEC Filing Analyzer.

This module defines domain-specific exceptions that provide clear error handling
and demonstrate professional exception management practices.
"""

from typing import Optional, Dict, Any


class AnalyzerBaseException(Exception):
    """
    Base exception class for all analyzer-specific exceptions.
    
    This follows the principle of creating a clear exception hierarchy
    for better error handling and debugging.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize base exception.
        
        Args:
            message: Human-readable error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AnalyzerBaseException):
    """
    Exception raised for data validation errors.
    
    This exception is used when input data doesn't meet validation requirements,
    providing specific field information for better user feedback.
    """
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        """
        Initialize validation error.
        
        Args:
            message: Validation error message
            field: Name of the field that failed validation
            value: The value that caused the validation error
        """
        super().__init__(message)
        self.field = field
        self.value = value
        self.details = {
            "field": field,
            "value": str(value) if value is not None else None,
            "type": "validation_error"
        }


class DocumentProcessingError(AnalyzerBaseException):
    """
    Exception raised when document processing fails.
    
    This includes errors in fetching, parsing, or processing SEC filing documents.
    """
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None):
        """
        Initialize document processing error.
        
        Args:
            message: Error message describing what went wrong
            url: The URL that caused the error
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.details = {
            "url": url,
            "status_code": status_code,
            "type": "document_processing_error"
        }


class AIServiceError(AnalyzerBaseException):
    """
    Exception raised when AI service operations fail.
    
    This covers errors from Google Gemini, Hugging Face, or other AI services.
    """
    
    def __init__(
        self, 
        message: str, 
        provider: Optional[str] = None,
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        """
        Initialize AI service error.
        
        Args:
            message: Error message from the AI service
            provider: Name of the AI provider (e.g., "Google Gemini")
            error_code: Provider-specific error code
            retry_after: Seconds to wait before retrying, if applicable
        """
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code
        self.retry_after = retry_after
        self.details = {
            "provider": provider,
            "error_code": error_code,
            "retry_after": retry_after,
            "type": "ai_service_error"
        }


class VectorStoreError(AnalyzerBaseException):
    """
    Exception raised when vector database operations fail.
    
    This covers errors in embedding generation, storage, or retrieval.
    """
    
    def __init__(self, message: str, operation: Optional[str] = None):
        """
        Initialize vector store error.
        
        Args:
            message: Error message describing the vector store issue
            operation: The operation that failed (e.g., "embedding", "search")
        """
        super().__init__(message)
        self.operation = operation
        self.details = {
            "operation": operation,
            "type": "vector_store_error"
        }


class ConfigurationError(AnalyzerBaseException):
    """
    Exception raised for configuration-related errors.
    
    This includes missing API keys, invalid settings, or misconfiguration issues.
    """
    
    def __init__(self, message: str, setting: Optional[str] = None):
        """
        Initialize configuration error.
        
        Args:
            message: Configuration error message
            setting: Name of the problematic setting
        """
        super().__init__(message)
        self.setting = setting
        self.details = {
            "setting": setting,
            "type": "configuration_error"
        }


class RateLimitError(AIServiceError):
    """
    Exception raised when API rate limits are exceeded.
    
    This is a specialized AI service error for rate limiting scenarios.
    """
    
    def __init__(
        self, 
        message: str = "API rate limit exceeded",
        provider: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        """
        Initialize rate limit error.
        
        Args:
            message: Rate limit error message
            provider: Name of the AI provider
            retry_after: Seconds to wait before retrying
        """
        super().__init__(
            message=message,
            provider=provider,
            error_code="RATE_LIMIT_EXCEEDED",
            retry_after=retry_after
        )


class TimeoutError(AnalyzerBaseException):
    """
    Exception raised when operations timeout.
    
    This covers timeouts in document fetching, AI processing, or other operations.
    """
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None):
        """
        Initialize timeout error.
        
        Args:
            message: Timeout error message
            timeout_seconds: The timeout value that was exceeded
        """
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.details = {
            "timeout_seconds": timeout_seconds,
            "type": "timeout_error"
        }


# Exception mapping for HTTP status codes
EXCEPTION_HTTP_MAPPING = {
    ValidationError: 422,
    DocumentProcessingError: 400,
    AIServiceError: 502,
    VectorStoreError: 500,
    ConfigurationError: 500,
    RateLimitError: 429,
    TimeoutError: 504
}


def get_http_status_code(exception: Exception) -> int:
    """
    Get appropriate HTTP status code for an exception.
    
    Args:
        exception: The exception to map
        
    Returns:
        int: Appropriate HTTP status code
    """
    exception_type = type(exception)
    
    # Check for exact type match first
    if exception_type in EXCEPTION_HTTP_MAPPING:
        return EXCEPTION_HTTP_MAPPING[exception_type]
    
    # Check for inheritance
    for exc_type, status_code in EXCEPTION_HTTP_MAPPING.items():
        if isinstance(exception, exc_type):
            return status_code
    
    # Default to 500 for unknown exceptions
    return 500


def format_error_response(exception: Exception) -> Dict[str, Any]:
    """
    Format an exception into a standardized error response.
    
    Args:
        exception: The exception to format
        
    Returns:
        Dict containing standardized error information
    """
    if isinstance(exception, AnalyzerBaseException):
        return {
            "error": type(exception).__name__,
            "message": exception.message,
            "details": exception.details
        }
    else:
        return {
            "error": type(exception).__name__,
            "message": str(exception),
            "details": {"type": "unexpected_error"}
        } 