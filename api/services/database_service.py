"""
Database Service - SQL Server Data Access Layer
Handles doctor validation and fraud case management against Azure SQL Database
"""

import logging
import os
import pyodbc
import uuid
from datetime import datetime
from services.credentials_service import get_sql_token_struct
from services.message_translations import get_message
from decorators.service_errors import handle_service_errors


@handle_service_errors("SQL Database")
def validate_doctor_in_database(doctor_info: dict, language: str = 'nl') -> dict:
    """
    Validate doctor information against Azure SQL Database to detect fraud
    Uses Entra ID (Azure AD) authentication for secure access
    Raises ServiceCallError on timeout or connection issues
    
    Searches database using extracted Content Understanding fields:
    - Primary: RIZIV number (exact match)
    - Fallback: Name + City/Address (fuzzy match)
    
    If no match found → FRAUD
    If match found → VALID
    
    Args:
        doctor_info: Dictionary with doctor information
        language: UI language selection (nl/fr/en) for message translation
    """
    global _cached_db_credential
    
    validation_result = {
        "is_valid": False,  # Default to invalid (fraud) until proven otherwise
        "doctor_found": False,
        "fraud_detected": True,  # Assume fraud until doctor is found
        "message": ""
    }
    
    try:
        # Get SQL Server connection details from environment
        server = os.environ.get("SQL_SERVER")
        database = os.environ.get("SQL_DATABASE")
        
        if not all([server, database]):
            logging.warning("SQL Server configuration incomplete")
            validation_result["message"] = get_message("db_config_missing", language)
            return validation_result
        
        # Get Azure AD token for SQL Database using shared cached credential
        token_struct = get_sql_token_struct()
        
        # SQL Server connection string with Azure AD authentication
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        logging.info(f"Connecting to SQL Server with Entra ID authentication: {server}")
        
        # Connect to database with Azure AD token
        SQL_COPT_SS_ACCESS_TOKEN = 1256  # Connection option for access token
        conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        cursor = conn.cursor()
        
        # Extract doctor information from Content Understanding output
        doctor_riziv = doctor_info.get("riziv", "").strip()
        doctor_name = doctor_info.get("name", "").strip()
        doctor_address = doctor_info.get("address", "").strip()
        doctor_phone = doctor_info.get("phone", "").strip()
        
        logging.info(f"Validating doctor - RIZIV: {doctor_riziv}, Name: {doctor_name}, Address: {doctor_address}")
        
        row_count = 0
        
        # Strategy 1: Search by RIZIV number (most reliable)
        if doctor_riziv:
            query = "SELECT first_name, last_name FROM dbo.doctors_riziv WHERE riziv_number = ?"
            cursor.execute(query, (doctor_riziv,))
            db_doctor = cursor.fetchone()
            
            if db_doctor:
                # RIZIV found - now verify the name matches
                db_first_name = (db_doctor[0] or "").strip()
                db_last_name = (db_doctor[1] or "").strip()
                db_full_name = f"{db_first_name} {db_last_name}".strip()
                
                # Clean and normalize names for comparison (remove titles, convert to uppercase)
                doc_name_clean = doctor_name.replace("Dr.", "").replace("Arts", "").replace("Doctor", "").replace(".", "").strip() if doctor_name else ""
                
                # Split document name into parts
                doc_name_parts = [part.upper() for part in doc_name_clean.split() if part]
                db_first_upper = db_first_name.upper()
                db_last_upper = db_last_name.upper()
                
                # Strict name matching: both first AND last name must match
                # Account for potential name order variations (FirstName LastName or LastName FirstName)
                name_matches = False
                
                if db_first_upper and db_last_upper and len(doc_name_parts) >= 2:
                    # Check if both first and last name appear in document (in any order)
                    has_first_name = db_first_upper in doc_name_parts
                    has_last_name = db_last_upper in doc_name_parts
                    
                    if has_first_name and has_last_name:
                        name_matches = True
                        logging.info(f"Name match confirmed: Document='{doctor_name}' contains both '{db_first_name}' and '{db_last_name}'")
                    else:
                        logging.warning(f"Name mismatch: Document='{doctor_name}' (parts: {doc_name_parts}) vs DB first='{db_first_name}' last='{db_last_name}'")
                elif not db_first_upper and db_last_upper:
                    # Only last name in database - check if it matches
                    name_matches = db_last_upper in doc_name_parts
                    if name_matches:
                        logging.info(f"Last name match (no first name in DB): '{db_last_name}' in '{doctor_name}'")
                
                if name_matches:
                    # Name matches - doctor verified
                    validation_result["doctor_found"] = True
                    validation_result["is_valid"] = True
                    validation_result["fraud_detected"] = False
                    validation_result["message"] = get_message("doctor_verified_riziv", language, riziv=doctor_riziv)
                    logging.info(f"✓ Doctor verified by RIZIV: {doctor_riziv}, name matches: '{doctor_name}' ≈ '{db_full_name}'")
                    row_count = 1
                else:
                    # RIZIV exists but name doesn't match - FRAUD!
                    validation_result["doctor_found"] = False
                    validation_result["is_valid"] = False
                    validation_result["fraud_detected"] = True
                    validation_result["fraud_type"] = "name_mismatch"
                    validation_result["message"] = get_message("fraud_name_mismatch", language, doc_name=doctor_name, db_name=db_full_name)
                    logging.error(f"✗ FRAUD DETECTED - RIZIV {doctor_riziv} exists but name mismatch: Document='{doctor_name}' vs Database='{db_full_name}'")
                    row_count = 0  # Treat as not found for fraud case creation
            else:
                logging.warning(f"RIZIV number not found in database: {doctor_riziv}")
        
        # Strategy 2: If RIZIV not found, try fuzzy match on name and location
        if row_count == 0 and doctor_name:
            # Split name into parts for flexible matching
            name_parts = doctor_name.replace("Dr.", "").replace("Arts", "").replace("Doctor", "").strip().split()
            
            if len(name_parts) >= 2:
                # Try matching last name (most reliable part)
                last_name = name_parts[-1]
                query = """
                    SELECT COUNT(*) 
                    FROM dbo.doctors_riziv 
                    WHERE last_name LIKE ?
                """
                cursor.execute(query, (f"%{last_name}%",))
                row_count = cursor.fetchone()[0]
                
                if row_count > 0:
                    # Further refine if address/city info available
                    if doctor_address:
                        city_match = None
                        # Try to extract city from address
                        if "," in doctor_address:
                            city_match = doctor_address.split(",")[-1].strip()
                        
                        if city_match:
                            query = """
                                SELECT COUNT(*) 
                                FROM dbo.doctors_riziv 
                                WHERE last_name LIKE ? AND city LIKE ?
                            """
                            cursor.execute(query, (f"%{last_name}%", f"%{city_match}%"))
                            refined_count = cursor.fetchone()[0]
                            
                            if refined_count > 0:
                                row_count = refined_count
                                validation_result["doctor_found"] = True
                                validation_result["is_valid"] = True
                                validation_result["fraud_detected"] = False
                                validation_result["message"] = get_message("doctor_verified_name_city", language, name=doctor_name)
                                logging.info(f"Doctor verified by name and city: {doctor_name}")
                            else:
                                row_count = 0  # Reset if refined search fails
                        else:
                            validation_result["doctor_found"] = True
                            validation_result["is_valid"] = True
                            validation_result["fraud_detected"] = False
                            validation_result["message"] = get_message("doctor_verified_name", language, name=doctor_name)
                            logging.info(f"Doctor verified by name: {doctor_name}")
        
        # Final result: If no match found anywhere → FRAUD
        if row_count == 0:
            validation_result["fraud_detected"] = True
            validation_result["is_valid"] = False
            validation_result["message"] = get_message("fraud_detected", language)
            if doctor_riziv:
                validation_result["message"] += f" (RIZIV: {doctor_riziv})"
            elif doctor_name:
                validation_result["message"] += f" (Naam: {doctor_name})"
            logging.error(f"FRAUD DETECTED - Doctor not found in database. RIZIV: {doctor_riziv}, Name: {doctor_name}")
        
        cursor.close()
        conn.close()
        
    except pyodbc.Error as db_error:
        logging.error(f"Database error during doctor validation: {str(db_error)}")
        validation_result["message"] = get_message("database_error", language, error=str(db_error))
    except Exception as e:
        logging.error(f"Error validating doctor: {str(e)}")
        validation_result["message"] = get_message("validation_error", language, error=str(e))
    
    return validation_result


@handle_service_errors("SQL Database")
def create_fraud_case(extracted_data: dict, fraud_reason: str, doctor_validation: dict, language: str = 'nl') -> dict:
    """
    Create a fraud case in the database when document is invalid or doctor not found
    Raises ServiceCallError on timeout or connection issues
    
    Args:
        extracted_data: Extracted document data
        fraud_reason: Reason for fraud detection
        doctor_validation: Doctor validation result
        language: UI language selection (nl/fr/en) for message translation
    
    Returns:
        dict with case_id and success status
    """
    result = {
        "success": False,
        "case_id": None,
        "message": ""
    }
    
    try:
        # Get SQL Server connection details from environment
        server = os.environ.get("SQL_SERVER")
        database = os.environ.get("SQL_DATABASE")
        
        if not all([server, database]):
            logging.warning("SQL Server configuration incomplete for fraud case creation")
            result["message"] = "Database configuratie ontbreekt"
            return result
        
        # Get Azure AD token for SQL Database using shared cached credential
        token_struct = get_sql_token_struct()
        
        # SQL Server connection string
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        logging.info(f"Creating fraud case in database")
        
        # Connect to database
        SQL_COPT_SS_ACCESS_TOKEN = 1256
        conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        cursor = conn.cursor()
        
        # Generate unique GUID for case_id
        case_id = str(uuid.uuid4())
        
        # Determine riziv_match_status
        riziv_match_status = "NOT_FOUND"
        if doctor_validation.get("doctor_found"):
            riziv_match_status = "FOUND"
        
        # Determine priority based on fraud reason
        priority_score = 5  # Default medium priority
        priority_reason = fraud_reason
        
        if "niet gevonden" in fraud_reason.lower():
            priority_score = 8  # High priority for unknown doctors
            priority_reason = "Arts niet in database - mogelijk fraude"
        elif "handtekening" in fraud_reason.lower():
            priority_score = 6
            priority_reason = "Ontbrekende handtekening"
        
        # Prepare document anomalies
        document_anomalies = fraud_reason
        
        # Insert fraud case with generated GUID
        insert_query = """
            INSERT INTO dbo.fraud_cases (
                case_id, submission_date, submission_channel, submitter_company,
                document_type, claimed_riziv_number, claimed_doctor_name,
                claimed_start_date, claimed_end_date, patient_identifier,
                riziv_match_status, document_anomalies, priority_score,
                priority_reason, case_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(
            insert_query,
            case_id,
            datetime.now(),
            "Online Portaal",
            "Automatisch Systeem",
            "Afwezigheidsattest",
            extracted_data.get("doctor_info", {}).get("riziv", ""),
            extracted_data.get("doctor_info", {}).get("name", ""),
            extracted_data.get("incapacity_start_date"),
            extracted_data.get("incapacity_end_date"),
            extracted_data.get("patient_national_number", ""),
            riziv_match_status,
            document_anomalies,
            priority_score,
            priority_reason,
            "NEW",
            datetime.now(),
            datetime.now()
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logging.info(f"Fraud case created successfully: {case_id}")
        
        result["success"] = True
        result["case_id"] = case_id
        result["message"] = f"Fraudemelding aangemaakt met referentienummer {case_id}"
        
        return result
        
    except Exception as e:
        logging.error(f"Error creating fraud case: {str(e)}")
        result["success"] = False
        result["message"] = get_message("fraud_case_creation_error", language, error=str(e))
        return result

