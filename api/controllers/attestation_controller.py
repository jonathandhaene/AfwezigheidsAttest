"""
Attestation Controller - Orchestration Layer
Coordinates the workflow between services without direct service-to-service coupling
"""

import logging
from datetime import datetime
from services.document_service import (
    analyze_document_with_content_understanding,
    extract_document_info,
    validate_attestation_rules
)
from services.database_service import validate_doctor_in_database, create_fraud_case
from services.message_translations import get_message
from decorators.service_errors import ServiceCallError, format_service_error_for_ui


def process_attestation(file_content: bytes, file_name: str, language: str = 'nl') -> dict:
    """
    Orchestrate the complete attestation processing workflow
    
    Workflow:
    1. Analyze document with Content Understanding
    2. Extract structured data
    3. Validate business rules (dates, signature)
    4. Validate doctor in database
    5. Create fraud case if needed
    6. Build and return result
    
    Args:
        file_content: Binary content of the uploaded file
        file_name: Name of the uploaded file
        language: UI language selection (nl/fr/en) for analyzer selection
        
    Returns:
        dict: Complete validation result with all details
    """
    try:
        # Step 1: Analyze document with Content Understanding
        logging.info(f"Step 1: Analyzing document: {file_name}")
        analysis_result = analyze_document_with_content_understanding(file_content, file_name, language)
        
        if not analysis_result.get("success"):
            # Analysis failed, return error
            return {
                "valid": False,
                "message": analysis_result.get("message", get_message("document_analysis_error", language)),
                "details": {}
            }
        
        # Step 2: Extract structured data from analysis result
        logging.info("Step 2: Extracting structured data from analysis")
        extracted_data = extract_document_info(analysis_result.get("result", {}))
        
        # Step 3: Validate business rules (dates, signature)
        logging.info("Step 3: Validating business rules")
        validation_errors = validate_attestation_rules(extracted_data, language)
        
        # Step 4: Validate doctor in database
        logging.info("Step 4: Validating doctor in database")
        doctor_validation = validate_doctor_in_database(extracted_data.get("doctor_info", {}), language)
        
        # Step 5: Determine if fraud case needs to be created
        fraud_detected = doctor_validation.get("fraud_detected", False)
        has_validation_errors = len(validation_errors) > 0
        
        # Step 6: Create fraud case if needed
        fraud_case_id = None
        if fraud_detected or has_validation_errors:
            logging.info("Step 5: Creating fraud case")
            
            if fraud_detected:
                fraud_reason = get_message("fraud_reason_not_found", language)
            else:
                fraud_reason = "; ".join(validation_errors)
            
            fraud_case = create_fraud_case(extracted_data, fraud_reason, doctor_validation, language)
            if fraud_case.get("success"):
                fraud_case_id = fraud_case.get("case_id")
                logging.info(f"Fraud case created: {fraud_case_id}")
        
        # Step 7: Build final result based on validation outcome
        logging.info("Step 6: Building final result")
        result = _build_result(
            extracted_data=extracted_data,
            validation_errors=validation_errors,
            doctor_validation=doctor_validation,
            fraud_case_id=fraud_case_id,
            file_name=file_name,
            language=language
        )
        
        return result
    
    except ServiceCallError as e:
        # Handle service errors (timeouts, connection issues, etc.)
        logging.error(f"Service call failed: {e.service_name} - {e.error_message}")
        error_result = format_service_error_for_ui(e)
        error_result["timestamp"] = datetime.now().isoformat()
        return error_result
        
    except Exception as e:
        logging.error(f"Error in attestation workflow: {str(e)}")
        return {
            "valid": False,
            "message": get_message("document_processing_error", language, error=str(e)),
            "details": {},
            "timestamp": datetime.now().isoformat()
        }


def _build_result(extracted_data: dict, validation_errors: list, doctor_validation: dict, 
                  fraud_case_id: str, file_name: str, language: str = 'nl') -> dict:
    """
    Build the final result dictionary based on validation outcomes
    
    Args:
        extracted_data: Data extracted from Content Understanding
        validation_errors: List of validation error messages
        doctor_validation: Doctor validation result from database
        fraud_case_id: Fraud case ID if created, None otherwise
        file_name: Original filename
        language: UI language selection (nl/fr/en) for message translations
        
    Returns:
        dict: Complete result with message and details
    """
    is_valid = len(validation_errors) == 0 and not doctor_validation.get("fraud_detected", False)
    
    # Build base details
    details = {
        "Bestandsnaam": file_name,
        "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "Status": "Goedgekeurd" if is_valid else "Afgekeurd",
        "Patiënt": extracted_data.get("patient_name", "Onbekend"),
        "Rijksregisternummer": extracted_data.get("patient_national_number", ""),
        "Geboortedatum": extracted_data.get("patient_birth_date", ""),
        "Adres patiënt": extracted_data.get("patient_address", ""),
        "Postcode en gemeente patiënt": extracted_data.get("patient_postal_code_city", ""),
        "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
        "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", get_message("not_found", language)),
        "Adres arts": extracted_data["doctor_info"].get("address", ""),
        "Postcode en gemeente arts": extracted_data["doctor_info"].get("postal_code_city", ""),
        "Telefoonnummer arts": extracted_data["doctor_info"].get("phone", "")
    }
    
    # Add fraud case ID if created
    if fraud_case_id:
        details["Zaak ID"] = fraud_case_id
    
    # Add optional fields
    if extracted_data.get("incapacity_start_date"):
        details["Onmogelijkheid vanaf"] = extracted_data["incapacity_start_date"]
    
    if extracted_data.get("incapacity_end_date"):
        details["Onmogelijkheid tot"] = extracted_data["incapacity_end_date"]
    
    if extracted_data.get("summary"):
        details["Samenvatting"] = extracted_data["summary"]
    
    if extracted_data.get("allowed_to_leave_house") is not None:
        details["Mag huis verlaten"] = get_message("yes", language) if extracted_data["allowed_to_leave_house"] else get_message("no", language)
    
    # Handle valid case
    if is_valid:
        # Add doctor verification message as warning
        if doctor_validation.get("message") and doctor_validation.get("doctor_found"):
            details["Waarschuwingen"] = [doctor_validation["message"]]
        
        return {
            "valid": True,
            "message": "Uw afwezigheidsattest is geldig en goedgekeurd.",
            "details": details
        }
    
    # Handle invalid cases
    details["Handtekening"] = "Ja" if extracted_data["has_signature"] else "Nee"
    
    # Fraud detected (doctor not found)
    if doctor_validation.get("fraud_detected"):
        details["Reden"] = get_message("fraud_reason_not_found", language)
        return {
            "valid": False,
            "message": "Het document is afgekeurd. De arts kon niet worden geverifieerd in onze database van geregistreerde artsen.",
            "details": details
        }
    
    # Validation errors
    details["Fouten"] = validation_errors
    return {
        "valid": False,
        "message": "Uw afwezigheidsattest kon niet worden goedgekeurd.",
        "details": details
    }
