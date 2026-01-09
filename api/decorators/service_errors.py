"""
Service Error Handling Utilities
Provides reusable error handling for outbound service calls (Azure AI, Database, etc.)
"""

import logging
from functools import wraps
from typing import Callable, Any
import requests
from azure.core.exceptions import (
    AzureError, 
    ServiceRequestError,
    ServiceResponseError,
    HttpResponseError
)


class ServiceCallError(Exception):
    """Base exception for service call failures"""
    def __init__(self, service_name: str, error_message: str, details: dict = None):
        self.service_name = service_name
        self.error_message = error_message
        self.details = details or {}
        super().__init__(f"{service_name}: {error_message}")


class ServiceTimeoutError(ServiceCallError):
    """Exception for service call timeouts"""
    def __init__(self, service_name: str, timeout_seconds: int):
        super().__init__(
            service_name,
            f"Service call timed out after {timeout_seconds} seconds",
            {"timeout_seconds": timeout_seconds}
        )


class ServiceConnectionError(ServiceCallError):
    """Exception for service connection failures"""
    def __init__(self, service_name: str, error_details: str):
        super().__init__(
            service_name,
            f"Failed to connect to service: {error_details}",
            {"connection_error": error_details}
        )


def handle_service_errors(service_name: str):
    """
    Decorator to handle errors from outbound service calls consistently
    
    Usage:
        @handle_service_errors("Azure Content Understanding")
        def call_azure_api():
            # Your service call here
            pass
    
    Args:
        service_name: Name of the service being called (e.g., "Azure Content Understanding", "SQL Database")
    
    Returns:
        Decorated function that catches and re-raises service errors in a consistent format
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            
            # Timeout errors
            except requests.exceptions.Timeout as e:
                logging.error(f"{service_name} call timed out: {str(e)}")
                raise ServiceTimeoutError(service_name, timeout_seconds=30)
            
            except TimeoutError as e:
                logging.error(f"{service_name} call timed out: {str(e)}")
                raise ServiceTimeoutError(service_name, timeout_seconds=30)
            
            # Connection errors
            except requests.exceptions.ConnectionError as e:
                logging.error(f"{service_name} connection failed: {str(e)}")
                raise ServiceConnectionError(service_name, str(e))
            
            except requests.exceptions.SSLError as e:
                logging.error(f"{service_name} SSL error: {str(e)}")
                raise ServiceConnectionError(service_name, f"SSL connection failed: {str(e)}")
            
            except ConnectionError as e:
                logging.error(f"{service_name} connection failed: {str(e)}")
                raise ServiceConnectionError(service_name, str(e))
            
            # Azure-specific errors
            except ServiceRequestError as e:
                logging.error(f"{service_name} request error: {str(e)}")
                raise ServiceConnectionError(service_name, str(e))
            
            except ServiceResponseError as e:
                logging.error(f"{service_name} response error: {str(e)}")
                raise ServiceCallError(service_name, f"Invalid response: {str(e)}")
            
            except HttpResponseError as e:
                logging.error(f"{service_name} HTTP error {e.status_code}: {str(e)}")
                raise ServiceCallError(
                    service_name,
                    f"HTTP {e.status_code}: {e.message if hasattr(e, 'message') else str(e)}",
                    {"status_code": e.status_code}
                )
            
            except AzureError as e:
                logging.error(f"{service_name} Azure error: {str(e)}")
                raise ServiceCallError(service_name, str(e))
            
            # Catch-all for requests exceptions (includes SSL errors wrapped in other exceptions)
            except requests.exceptions.RequestException as e:
                logging.error(f"{service_name} request exception: {str(e)}")
                error_msg = str(e)
                if "SSLError" in error_msg or "SSL" in error_msg or "EOF occurred" in error_msg:
                    raise ServiceConnectionError(service_name, f"SSL/Connection error: {error_msg}")
                raise ServiceCallError(service_name, error_msg)
            
            # Database errors
            except Exception as e:
                # Check for common database timeout patterns
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['timeout', 'timed out', 'connection timeout']):
                    logging.error(f"{service_name} database timeout: {str(e)}")
                    raise ServiceTimeoutError(service_name, timeout_seconds=30)
                
                # Check for connection issues
                if any(keyword in error_str for keyword in ['connection', 'connect', 'network']):
                    logging.error(f"{service_name} connection error: {str(e)}")
                    raise ServiceConnectionError(service_name, str(e))
                
                # Generic service error
                logging.error(f"{service_name} unexpected error: {str(e)}")
                raise ServiceCallError(service_name, str(e))
        
        return wrapper
    return decorator


def format_service_error_for_ui(error: ServiceCallError) -> dict:
    """
    Format a service error for display in the UI
    
    Args:
        error: ServiceCallError or subclass
    
    Returns:
        dict: Formatted error for UI display with red bullet styling
    """
    error_type = "timeout" if isinstance(error, ServiceTimeoutError) else "connection" if isinstance(error, ServiceConnectionError) else "error"
    
    return {
        "valid": False,
        "message": f"❌ Service call failed: {error.service_name}",
        "details": {
            "Service": error.service_name,
            "Error Type": error_type.title(),
            "Error Message": error.error_message,
            **error.details
        },
        "error_category": error_type,
        "timestamp": None  # Will be added by controller
    }
