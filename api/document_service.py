"""
Document Service - Business Logic Layer
Handles document analysis, validation, and processing
"""

import logging
import os
from datetime import datetime, date
from dateutil import parser
from content_understanding_client import ContentUnderstandingClient
from database_service import validate_doctor_in_database, create_fraud_case
from credentials_service import get_credential

# Cache the client at module level to reuse across requests
_cached_client = None


def analyze_document_with_content_understanding(file_content: bytes, file_name: str) -> dict:
    """
    Analyze document using Azure Content Understanding
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
        
        # Extract information from the result
        extracted_data = extract_document_info(result)
        
        # Validate the document
        return validate_attestation(extracted_data, file_name)
        
    except Exception as e:
        logging.error(f"Error analyzing document: {str(e)}")
        return {
            "valid": False,
            "message": f"Fout bij het analyseren van het document: {str(e)}",
            "details": {}
        }


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


def validate_attestation(extracted_data: dict, file_name: str) -> dict:
    """
    Validate the attestation based on extracted structured data
    """
    today = date.today()
    validation_errors = []
    validation_warnings = []
    
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
            if end_date > today:
                validation_warnings.append(
                    f"Onmogelijheid einddatum ligt in de toekomst: {end_date.strftime('%d-%m-%Y')} (dit kan geldig zijn)"
                )
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
    
    # Validate doctor information in database
    doctor_validation = validate_doctor_in_database(extracted_data.get("doctor_info", {}))
    
    # If fraud detected, create fraud case and reject
    if doctor_validation["fraud_detected"]:
        fraud_reason = "Arts niet gevonden in geregistreerde artsen database"
        fraud_case = create_fraud_case(extracted_data, fraud_reason, doctor_validation)
        
        details = {
            "Bestandsnaam": file_name,
            "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "Status": "Afgekeurd",
            "Patiënt": extracted_data.get("patient_name", "Onbekend"),
            "Rijksregisternummer": extracted_data.get("patient_national_number", ""),
            "Geboortedatum": extracted_data.get("patient_birth_date", ""),
            "Adres patiënt": extracted_data.get("patient_address", ""),
            "Postcode en gemeente patiënt": extracted_data.get("patient_postal_code_city", ""),
            "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
            "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", "Niet gevonden"),
            "Adres arts": extracted_data["doctor_info"].get("address", ""),
            "Postcode en gemeente arts": extracted_data["doctor_info"].get("postal_code_city", ""),
            "Telefoonnummer arts": extracted_data["doctor_info"].get("phone", ""),
            "Reden": fraud_reason
        }
        
        # Add fraud case ID if created successfully
        if fraud_case["success"]:
            details["Zaak ID"] = fraud_case["case_id"]
            logging.info(f"Fraud case created: {fraud_case['case_id']}")
        
        return {
            "valid": False,
            "message": "Het document is afgekeurd. De arts kon niet worden geverifieerd in onze database van geregistreerde artsen.",
            "details": details
        }
    
    # Add validation message if doctor was found
    if doctor_validation["message"] and doctor_validation["doctor_found"]:
        validation_warnings.append(doctor_validation["message"])
    
    # Determine if valid
    is_valid = len(validation_errors) == 0
    
    # Build result
    if is_valid:
        details = {
            "Bestandsnaam": file_name,
            "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "Status": "Goedgekeurd",
            "Patiënt": extracted_data.get("patient_name", "Onbekend"),
            "Rijksregisternummer": extracted_data.get("patient_national_number", ""),
            "Geboortedatum": extracted_data.get("patient_birth_date", ""),
            "Adres patiënt": extracted_data.get("patient_address", ""),
            "Postcode en gemeente patiënt": extracted_data.get("patient_postal_code_city", ""),
            "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
            "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", "Niet gevonden"),
            "Adres arts": extracted_data["doctor_info"].get("address", ""),
            "Postcode en gemeente arts": extracted_data["doctor_info"].get("postal_code_city", ""),
            "Telefoonnummer arts": extracted_data["doctor_info"].get("phone", "")
        }
        
        if extracted_data.get("incapacity_start_date"):
            details["Onmogelijkheid vanaf"] = extracted_data["incapacity_start_date"]
        
        if extracted_data.get("incapacity_end_date"):
            details["Onmogelijkheid tot"] = extracted_data["incapacity_end_date"]
        
        if extracted_data.get("summary"):
            details["Samenvatting"] = extracted_data["summary"]
        
        if extracted_data.get("allowed_to_leave_house") is not None:
            details["Mag huis verlaten"] = "Ja" if extracted_data["allowed_to_leave_house"] else "Nee"
        
        if validation_warnings:
            details["Waarschuwingen"] = validation_warnings
        
        return {
            "valid": True,
            "message": "Uw afwezigheidsattest is geldig en goedgekeurd.",
            "details": details
        }
    else:
        # Document has validation errors - create fraud case
        fraud_reason = "; ".join(validation_errors)
        fraud_case = create_fraud_case(extracted_data, fraud_reason, doctor_validation)
        
        details = {
            "Bestandsnaam": file_name,
            "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "Status": "Afgekeurd",
            "Patiënt": extracted_data.get("patient_name", "Onbekend"),
            "Rijksregisternummer": extracted_data.get("patient_national_number", ""),
            "Geboortedatum": extracted_data.get("patient_birth_date", ""),
            "Adres patiënt": extracted_data.get("patient_address", ""),
            "Postcode en gemeente patiënt": extracted_data.get("patient_postal_code_city", ""),
            "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
            "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", "Niet gevonden"),
            "Adres arts": extracted_data["doctor_info"].get("address", ""),
            "Postcode en gemeente arts": extracted_data["doctor_info"].get("postal_code_city", ""),
            "Telefoonnummer arts": extracted_data["doctor_info"].get("phone", ""),
            "Handtekening": "Ja" if extracted_data["has_signature"] else "Nee",
            "Fouten": validation_errors
        }
        
        # Add fraud case ID if created successfully
        if fraud_case["success"]:
            details["Zaak ID"] = fraud_case["case_id"]
            logging.info(f"Fraud case created: {fraud_case['case_id']}")
        
        if extracted_data.get("incapacity_start_date"):
            details["Onmogelijkheid vanaf"] = extracted_data["incapacity_start_date"]
        
        if extracted_data.get("incapacity_end_date"):
            details["Onmogelijkheid tot"] = extracted_data["incapacity_end_date"]
        
        if extracted_data.get("allowed_to_leave_house") is not None:
            details["Mag huis verlaten"] = "Ja" if extracted_data["allowed_to_leave_house"] else "Nee"
        
        return {
            "valid": False,
            "message": "Uw afwezigheidsattest kon niet worden goedgekeurd.",
            "details": details
        }
