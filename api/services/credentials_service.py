"""
Credentials Service - Centralized Authentication Management
Provides cached Azure AD credentials for all services

IMPORTANT: Uses different credential types for local vs Azure environments:
- Local development: InteractiveBrowserCredential (opens browser for login)
- Azure Functions: DefaultAzureCredential (uses Managed Identity)
"""

import logging
import os
import struct
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# Single cached credential shared across all services
_cached_credential = None


def _is_running_in_azure():
    """
    Detect if running in Azure Functions environment
    """
    # Azure Functions sets these environment variables
    return (
        os.environ.get("WEBSITE_INSTANCE_ID") is not None or
        os.environ.get("FUNCTIONS_WORKER_RUNTIME") is not None and
        os.environ.get("HOME", "").startswith("/home")
    )


def clear_credential():
    """
    Clear the cached credential to force a fresh authentication
    """
    global _cached_credential
    _cached_credential = None
    logging.info("Cleared cached Azure AD credential")


def is_authenticated():
    """
    Check if user is already authenticated without triggering interactive login
    Returns True if credentials exist and have a valid cached token
    """
    global _cached_credential
    
    if _cached_credential is None:
        return False
    
    try:
        # Try to get token without interactive prompt (use cached token only)
        token = _cached_credential.get_token("https://database.windows.net/.default")
        return token is not None and token.token is not None
    except Exception as e:
        logging.debug(f"Token check failed: {str(e)}")
        return False


def get_credential():
    """
    Get or create the cached Azure AD credential
    
    Uses DefaultAzureCredential in Azure (Managed Identity) 
    and InteractiveBrowserCredential locally (opens browser)
    """
    global _cached_credential
    
    if _cached_credential is None:
        tenant_id = os.environ.get("AZURE_TENANT_ID")
        
        if _is_running_in_azure():
            # Running in Azure - use Managed Identity via DefaultAzureCredential
            logging.info("Running in Azure - using DefaultAzureCredential (Managed Identity)")
            _cached_credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=True,
                exclude_shared_token_cache_credential=True
            )
        else:
            # Local development - use interactive browser login
            logging.info(f"Running locally - using InteractiveBrowserCredential for tenant: {tenant_id}")
            if tenant_id:
                _cached_credential = InteractiveBrowserCredential(tenant_id=tenant_id)
            else:
                _cached_credential = InteractiveBrowserCredential()
    
    return _cached_credential


def get_sql_token_struct():
    """
    Get SQL Database authentication token as struct for pyodbc
    """
    credential = get_credential()
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    return token_struct
