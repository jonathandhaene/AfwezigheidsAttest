"""
Simplified Azure Content Understanding Client for Azure Functions
Based on: https://github.com/Azure-Samples/azure-ai-content-understanding-python
"""

import json
import logging
import requests
import time
from typing import Dict, Any, Optional
from requests.models import Response
from azure.identity import DefaultAzureCredential


POLL_TIMEOUT_SECONDS = 180


class ContentUnderstandingClient:
    """Simplified client for Azure Content Understanding API"""
    
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        credential: Optional[DefaultAzureCredential] = None,
        api_version: str = "2025-11-01"
    ):
        """
        Initialize the Content Understanding client.
        
        Args:
            endpoint: Azure Content Understanding endpoint (e.g., https://your-resource.services.ai.azure.com/)
            api_key: Subscription key for authentication (optional if using credential)
            credential: Azure credential for authentication (optional if using api_key)
            api_version: API version to use (default: 2025-11-01)
        """
        if not endpoint:
            raise ValueError("Endpoint is required")
        
        if not api_key and not credential:
            raise ValueError("Either api_key or credential must be provided")
        
        self._endpoint = endpoint.rstrip("/")
        self._api_version = api_version
        self._logger = logging.getLogger(__name__)
        self._credential = credential
        self._token = None
        self._token_expiry = 0
        
        if api_key:
            self._headers = {
                "Ocp-Apim-Subscription-Key": api_key,
                "x-ms-useragent": "afwezigheidsattest-app"
            }
        else:
            self._headers = {
                "x-ms-useragent": "afwezigheidsattest-app"
            }
    
    def _get_auth_header(self) -> Dict[str, str]:
        """Get authentication headers, refreshing token if needed."""
        if self._credential:
            # Check if token needs refresh (refresh 5 minutes before expiry)
            current_time = time.time()
            if current_time >= self._token_expiry - 300:
                token = self._credential.get_token("https://cognitiveservices.azure.com/.default")
                self._token = token.token
                self._token_expiry = token.expires_on
            
            headers = self._headers.copy()
            headers["Authorization"] = f"Bearer {self._token}"
            return headers
        else:
            return self._headers.copy()
    
    def analyze_document(self, file_bytes: bytes, analyzer_id: str = "prebuilt-layout") -> Dict[str, Any]:
        """
        Analyze a document using Azure Content Understanding.
        
        Args:
            file_bytes: The document bytes to analyze
            analyzer_id: The analyzer to use (default: prebuilt-layout)
        
        Returns:
            Analysis result as a dictionary
        """
        # Start analysis
        analyze_url = f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyzeBinary?api-version={self._api_version}"
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/octet-stream"
        
        self._logger.info(f"Sending document to Content Understanding API with analyzer: {analyzer_id}")
        
        response = requests.post(
            url=analyze_url,
            headers=headers,
            data=file_bytes
        )
        
        self._raise_for_status(response)
        
        # Poll for result
        result = self._poll_result(response)
        return result
    
    def _poll_result(
        self,
        response: Response,
        timeout_seconds: int = POLL_TIMEOUT_SECONDS,
        polling_interval_seconds: int = 2
    ) -> Dict[str, Any]:
        """
        Poll for the result of an async operation.
        
        Args:
            response: Initial response with operation-location header
            timeout_seconds: Maximum time to wait
            polling_interval_seconds: Time between polls
        
        Returns:
            The completed operation result
        """
        operation_location = response.headers.get("operation-location")
        if not operation_location:
            raise ValueError("No operation-location header in response")
        
        self._logger.info(f"Polling for results at: {operation_location}")
        
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
            
            poll_response = requests.get(operation_location, headers=self._get_auth_header())
            self._raise_for_status(poll_response)
            
            result = poll_response.json()
            status = result.get("status", "").lower()
            
            if status == "succeeded":
                self._logger.info(f"Analysis completed after {elapsed_time:.2f} seconds")
                return result
            elif status == "failed":
                error_msg = result.get("error", {}).get("message", "Unknown error")
                self._logger.error(f"Analysis failed: {error_msg}")
                raise RuntimeError(f"Analysis failed: {error_msg}")
            else:
                self._logger.debug(f"Analysis in progress... ({status})")
            
            time.sleep(polling_interval_seconds)
    
    def _raise_for_status(self, response: Response) -> None:
        """Raise exception with detailed error information"""
        if response.ok:
            return
        
        error_detail = ""
        try:
            error_json = response.json()
            if "error" in error_json:
                error_info = error_json["error"]
                error_code = error_info.get("code", "Unknown")
                error_message = error_info.get("message", "No message")
                error_detail = f"\nError Code: {error_code}\nMessage: {error_message}"
        except (ValueError, json.JSONDecodeError):
            if response.text:
                error_detail = f"\nResponse: {response.text[:500]}"
        
        error_msg = f"{response.status_code} {response.reason} for {response.url}{error_detail}"
        self._logger.error(error_msg)
        response.raise_for_status()
