"""
Credentials Service - Centralized Authentication Management
Provides cached Azure AD credentials for all services
"""

import logging
import os
import struct
from azure.identity import InteractiveBrowserCredential

# Single cached credential shared across all services
_cached_credential = None


def get_credential():
    """
    Get or create the cached Azure AD credential
    Returns the same credential instance for all calls
    """
    global _cached_credential
    
    if _cached_credential is None:
        tenant_id = os.environ.get("AZURE_TENANT_ID", "a3bf65f3-481b-404c-b69d-67e5bd9911af")
        logging.info(f"Creating cached Azure AD credential for tenant: {tenant_id}")
        _cached_credential = InteractiveBrowserCredential(tenant_id=tenant_id)
    
    return _cached_credential


def get_sql_token_struct():
    """
    Get SQL Database authentication token as struct for pyodbc
    """
    credential = get_credential()
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    return token_struct
