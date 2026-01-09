"""
Document Service - Business Logic Layer
Handles document analysis, validation, and processing
"""

import logging
import os
from datetime import datetime, date
from dateutil import parser
from content_understanding_client import ContentUnderstandingClient
from services.credentials_service import get_credential
from decorators.service_errors import handle_service_errors

# Cache the client at module level to reuse across requests
_cached_client = None


@handle_service_errors("Azure Content Understanding")
def analyze_document_with_content_understanding(file_content: bytes, file_name: str) -> dict:
    """
    Analyze document using Azure Content Understanding
    Raises ServiceCallError on timeout or connection issues
    """
    global _cached_credential, _cached_client
    
    try:
        # Get Azure Content Understanding configuration from environment
        endpoint = os.environ.get("AZURE_CONTENT_UNDERSTANDING_ENDPOINT")
        api_key = os.environ.get("AZURE_CONTENT_UNDERSTANDING_KEY")
        analyzer_id = os.environ.get("AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID", "prebuilt-layout")
        
        if not endpoint:
            logging.warning("Azure Content Understanding endpoint not configured")
            return {
                "valid": False,
                "message": "Azure Content Understanding is niet geconfigureerd. Configureer de omgevingsvariabele AZURE_CONTENT_UNDERSTANDING_ENDPOINT.",
                "details": {}
            }
        
        # Initialize Content Understanding client with cached credential/client to avoid repeated logins
        if _cached_client is None:
            if api_key:
                logging.info("Using API key authentication")
                _cached_client = ContentUnderstandingClient(
                    endpoint=endpoint,
                    api_key=api_key
                )
            else:
                logging.info("Using Azure AD authentication with shared cached credential")
                _cached_client = ContentUnderstandingClient(
                    endpoint=endpoint,
                    credential=get_credential()
                )
        
        # Analyze document with configured analyzer
        logging.info(f"Analyzing document: {file_name} with analyzer: {analyzer_id}")
        result = _cached_client.analyze_document(file_content, analyzer_id=analyzer_id)
        
        logging.info("Document analysis completed")
        
        return {
            "success": True,
            "result": result
        }
    
    # Let configuration errors fall through (not service errors)
    except ValueError as e:
        logging.error(f"Configuration error: {str(e)}")
        return {
            "success": False,
            "message": f"Configuratiefout: {str(e)}"
        }
    # All other exceptions (timeouts, connection errors, etc.) are handled by the decorator


def extract_document_info(result: dict) -> dict:
    """
    Extract relevant information from Content Understanding result using structured fields
    """
    extracted_data = {
        "patient_name": "",
        "patient_national_number": "",
        "patient_birth_date": "",
        "patient_address": "",
        "patient_postal_code_city": "",
        "incapacity_start_date": None,
        "incapacity_end_date": None,
        "certificate_date": None,
        "has_signature": False,
        "allowed_to_leave_house": None,
        "doctor_info": {
            "name": "",
            "riziv": "",
            "address": "",
            "postal_code_city": "",
            "phone": ""
        },
        "summary": ""
    }
    
    try:
        # Get the fields from the correct path: result -> result -> contents[0] -> fields
        analyze_result = result.get("result", {})
        contents = analyze_result.get("contents", [])
        
        if not contents:
            logging.error("No contents found in Content Understanding result")
            return extracted_data
        
        # Get fields from the first content item
        fields = contents[0].get("fields", {})
        logging.info(f"Extracted {len(fields)} fields from document")
        
        # Extract patient information
        if "PatientName" in fields:
            extracted_data["patient_name"] = fields["PatientName"].get("valueString", "")
        
        if "PatientNationalNumber" in fields:
            extracted_data["patient_national_number"] = fields["PatientNationalNumber"].get("valueString", "")
        
        if "PatientBirthDate" in fields:
            extracted_data["patient_birth_date"] = fields["PatientBirthDate"].get("valueDate", "")
        
        if "PatientAddress" in fields:
            extracted_data["patient_address"] = fields["PatientAddress"].get("valueString", "")
        
        if "PatientPostalCodeCity" in fields:
            extracted_data["patient_postal_code_city"] = fields["PatientPostalCodeCity"].get("valueString", "")
        
        # Extract incapacity dates
        if "IncapacityStartDate" in fields:
            extracted_data["incapacity_start_date"] = fields["IncapacityStartDate"].get("valueDate", None)
        
        if "IncapacityEndDate" in fields:
            extracted_data["incapacity_end_date"] = fields["IncapacityEndDate"].get("valueDate", None)
        
        if "CertificateDate" in fields:
            extracted_data["certificate_date"] = fields["CertificateDate"].get("valueDate", None)
        
        # Extract doctor signature and patient restrictions
        if "DoctorHasSigned" in fields:
            extracted_data["has_signature"] = fields["DoctorHasSigned"].get("valueBoolean", False)
        
        if "IsAllowedToLeaveHouse" in fields:
            extracted_data["allowed_to_leave_house"] = fields["IsAllowedToLeaveHouse"].get("valueBoolean", None)
        
        # Extract doctor information
        if "DoctorName" in fields:
            extracted_data["doctor_info"]["name"] = fields["DoctorName"].get("valueString", "")
        
        if "DoctorRizivNumber" in fields:
            extracted_data["doctor_info"]["riziv"] = fields["DoctorRizivNumber"].get("valueString", "")
        
        if "DoctorAddress" in fields:
            extracted_data["doctor_info"]["address"] = fields["DoctorAddress"].get("valueString", "")
        
        if "DoctorPostalCodeCity" in fields:
            extracted_data["doctor_info"]["postal_code_city"] = fields["DoctorPostalCodeCity"].get("valueString", "")
        
        if "DoctorPhoneNumber" in fields:
            extracted_data["doctor_info"]["phone"] = fields["DoctorPhoneNumber"].get("valueString", "")
        
        # Extract summary
        if "Summary" in fields:
            extracted_data["summary"] = fields["Summary"].get("valueString", "")
        
        logging.info(f"Extracted structured data - Patient: {extracted_data['patient_name']}, Doctor: {extracted_data['doctor_info']['name']}, RIZIV: {extracted_data['doctor_info']['riziv']}, Signature: {extracted_data['has_signature']}")
        logging.info(f"Patient details - Birth: {extracted_data.get('patient_birth_date')}, Address: {extracted_data.get('patient_address')}, Postal: {extracted_data.get('patient_postal_code_city')}")
        logging.info(f"Doctor details - Address: {extracted_data['doctor_info'].get('address')}, Postal: {extracted_data['doctor_info'].get('postal_code_city')}, Phone: {extracted_data['doctor_info'].get('phone')}")
    
    except Exception as e:
        logging.error(f"Error extracting document info: {str(e)}")
    
    return extracted_data


def validate_attestation_rules(extracted_data: dict) -> list:
    """
    Validate business rules (dates, signature) without external dependencies
    Returns list of validation error messages
    """
    today = date.today()
    validation_errors = []
    
    # Check incapacity start date
    if extracted_data.get("incapacity_start_date"):
        try:
            start_date = parser.parse(extracted_data["incapacity_start_date"]).date()
            if start_date > today:
                validation_errors.append(
                    f"Onmogelijheid startdatum ligt in de toekomst: {start_date.strftime('%d-%m-%Y')}"
                )
        except (ValueError, TypeError, parser.ParserError) as e:
            logging.warning(f"Could not parse incapacity start date: {e}")
    
    # Check incapacity end date
    if extracted_data.get("incapacity_end_date"):
        try:
            end_date = parser.parse(extracted_data["incapacity_end_date"]).date()
            # Future end dates are allowed (warnings only, not errors)
            # Removed validation_warnings as this function only returns errors
        except (ValueError, TypeError, parser.ParserError) as e:
            logging.warning(f"Could not parse incapacity end date: {e}")
    
    # Check certificate date
    if extracted_data.get("certificate_date"):
        try:
            cert_date = parser.parse(extracted_data["certificate_date"]).date()
            if cert_date > today:
                validation_errors.append(
                    f"Certificaat datum ligt in de toekomst: {cert_date.strftime('%d-%m-%Y')}"
                )
        except (ValueError, TypeError, parser.ParserError) as e:
            logging.warning(f"Could not parse certificate date: {e}")
    
    # Check for signature
    if not extracted_data["has_signature"]:
        validation_errors.append("Er ontbreekt een handtekening van de arts op het document")
    
    return validation_errors
