"""
Azure Functions App - Python v2 Programming Model
Main entry point for all HTTP-triggered functions
"""

import azure.functions as func
import logging
import json
import os
import pyodbc
import struct
from datetime import datetime, date
from dateutil import parser
from content_understanding_client import ContentUnderstandingClient
from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def analyze_document_with_content_understanding(file_content: bytes, file_name: str) -> dict:
    """
    Analyze document using Azure Content Understanding
    """
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
        
        # Initialize Content Understanding client with either API key or Azure AD
        if api_key:
            logging.info("Using API key authentication")
            client = ContentUnderstandingClient(
                endpoint=endpoint,
                api_key=api_key
            )
        else:
            logging.info("Using Azure AD authentication")
            credential = DefaultAzureCredential()
            client = ContentUnderstandingClient(
                endpoint=endpoint,
                credential=credential
            )
        
        # Analyze document with configured analyzer
        logging.info(f"Analyzing document: {file_name} with analyzer: {analyzer_id}")
        result = client.analyze_document(file_content, analyzer_id=analyzer_id)
        
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

def validate_doctor_in_database(doctor_info: dict) -> dict:
    """
    Validate doctor information against Azure SQL Database to detect fraud
    Uses Entra ID (Azure AD) authentication for secure access
    
    Searches database using extracted Content Understanding fields:
    - Primary: RIZIV number (exact match)
    - Fallback: Name + City/Address (fuzzy match)
    
    If no match found → FRAUD
    If match found → VALID
    """
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
            validation_result["message"] = "Database configuratie ontbreekt - kan validatie niet uitvoeren"
            return validation_result
        
        # Get Azure AD token for SQL Database
        credential = DefaultAzureCredential()
        token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
        token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        
        # SQL Server connection string with Azure AD authentication
        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
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
            query = "SELECT COUNT(*) FROM dbo.doctors_riziv WHERE riziv_number = ?"
            cursor.execute(query, (doctor_riziv,))
            row_count = cursor.fetchone()[0]
            
            if row_count > 0:
                validation_result["doctor_found"] = True
                validation_result["is_valid"] = True
                validation_result["fraud_detected"] = False
                validation_result["message"] = f"Arts geverifieerd via RIZIV nummer: {doctor_riziv}"
                logging.info(f"Doctor verified by RIZIV: {doctor_riziv}")
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
                                validation_result["message"] = f"Arts geverifieerd via naam en stad: {doctor_name}"
                                logging.info(f"Doctor verified by name and city: {doctor_name}")
                            else:
                                row_count = 0  # Reset if refined search fails
                        else:
                            validation_result["doctor_found"] = True
                            validation_result["is_valid"] = True
                            validation_result["fraud_detected"] = False
                            validation_result["message"] = f"Arts geverifieerd via naam: {doctor_name}"
                            logging.info(f"Doctor verified by name: {doctor_name}")
        
        # Final result: If no match found anywhere → FRAUD
        if row_count == 0:
            validation_result["fraud_detected"] = True
            validation_result["is_valid"] = False
            validation_result["message"] = "⚠️ FRAUDE GEDETECTEERD: Arts niet gevonden in geregistreerde artsendatabase"
            if doctor_riziv:
                validation_result["message"] += f" (RIZIV: {doctor_riziv})"
            elif doctor_name:
                validation_result["message"] += f" (Naam: {doctor_name})"
            logging.error(f"FRAUD DETECTED - Doctor not found in database. RIZIV: {doctor_riziv}, Name: {doctor_name}")
        
        cursor.close()
        conn.close()
        
    except pyodbc.Error as db_error:
        logging.error(f"Database error during doctor validation: {str(db_error)}")
        validation_result["message"] = f"Database fout: {str(db_error)}"
    except Exception as e:
        logging.error(f"Error validating doctor: {str(e)}")
        validation_result["message"] = f"Fout bij validatie: {str(e)}"
    
    return validation_result

def extract_document_info(result: dict) -> dict:
    """
    Extract relevant information from Content Understanding result using structured fields
    """
    extracted_data = {
        "patient_name": "",
        "patient_national_number": "",
        "incapacity_start_date": None,
        "incapacity_end_date": None,
        "certificate_date": None,
        "has_signature": False,
        "doctor_info": {
            "name": "",
            "riziv": "",
            "address": "",
            "phone": ""
        },
        "summary": ""
    }
    
    try:
        # Get the analysis result and structured fields
        analyze_result = result.get("analyzeResult", {})
        fields = analyze_result.get("fields", {})
        
        # Extract patient information
        if "PatientName" in fields:
            extracted_data["patient_name"] = fields["PatientName"].get("valueString", "")
        
        if "PatientNationalNumber" in fields:
            extracted_data["patient_national_number"] = fields["PatientNationalNumber"].get("valueString", "")
        
        # Extract incapacity dates
        if "IncapacityStartDate" in fields:
            extracted_data["incapacity_start_date"] = fields["IncapacityStartDate"].get("valueDate", None)
        
        if "IncapacityEndDate" in fields:
            extracted_data["incapacity_end_date"] = fields["IncapacityEndDate"].get("valueDate", None)
        
        if "CertificateDate" in fields:
            extracted_data["certificate_date"] = fields["CertificateDate"].get("valueDate", None)
        
        # Extract doctor signature
        if "DoctorHasSigned" in fields:
            extracted_data["has_signature"] = fields["DoctorHasSigned"].get("valueBoolean", False)
        
        # Extract doctor information
        if "DoctorName" in fields:
            extracted_data["doctor_info"]["name"] = fields["DoctorName"].get("valueString", "")
        
        if "DoctorRizivNumber" in fields:
            extracted_data["doctor_info"]["riziv"] = fields["DoctorRizivNumber"].get("valueString", "")
        
        if "DoctorAddress" in fields:
            extracted_data["doctor_info"]["address"] = fields["DoctorAddress"].get("valueString", "")
        
        if "DoctorPhoneNumber" in fields:
            extracted_data["doctor_info"]["phone"] = fields["DoctorPhoneNumber"].get("valueString", "")
        
        # Extract summary
        if "Summary" in fields:
            extracted_data["summary"] = fields["Summary"].get("valueString", "")
        
        logging.info(f"Extracted structured data - Patient: {extracted_data['patient_name']}, Doctor: {extracted_data['doctor_info']['name']}, RIZIV: {extracted_data['doctor_info']['riziv']}, Signature: {extracted_data['has_signature']}")
        
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
    
    # If fraud detected, immediately reject
    if doctor_validation["fraud_detected"]:
        return {
            "valid": False,
            "message": "⚠️ DOCUMENT AFGEWEZEN - FRAUDE GEDETECTEERD!",
            "details": {
                "Bestandsnaam": file_name,
                "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "Status": "🚫 AFGEKEURD - FRAUDE",
                "Patiënt": extracted_data.get("patient_name", "Onbekend"),
                "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
                "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", "Niet gevonden"),
                "Reden": doctor_validation["message"],
                "Fouten": [doctor_validation["message"]] + validation_errors
            }
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
            "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
            "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", "Niet gevonden")
        }
        
        if extracted_data.get("incapacity_start_date"):
            details["Onmogelijkheid vanaf"] = extracted_data["incapacity_start_date"]
        
        if extracted_data.get("incapacity_end_date"):
            details["Onmogelijkheid tot"] = extracted_data["incapacity_end_date"]
        
        if extracted_data.get("summary"):
            details["Samenvatting"] = extracted_data["summary"]
        
        if validation_warnings:
            details["Waarschuwingen"] = validation_warnings
        
        return {
            "valid": True,
            "message": "✓ Uw afwezigheidsattest is geldig en geaccepteerd.",
            "details": details
        }
    else:
        details = {
            "Bestandsnaam": file_name,
            "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "Status": "Afgekeurd",
            "Aantal fouten": len(validation_errors),
            "Patiënt": extracted_data.get("patient_name", "Onbekend"),
            "Arts": extracted_data["doctor_info"].get("name", "Onbekend"),
            "RIZIV Nummer": extracted_data["doctor_info"].get("riziv", "Niet gevonden"),
            "Handtekening aanwezig": "Ja" if extracted_data["has_signature"] else "Nee"
        }
        
        if extracted_data.get("incapacity_start_date"):
            details["Onmogelijkheid vanaf"] = extracted_data["incapacity_start_date"]
        
        if extracted_data.get("incapacity_end_date"):
            details["Onmogelijkheid tot"] = extracted_data["incapacity_end_date"]
        
        return {
            "valid": False,
            "message": "✗ Uw afwezigheidsattest is ongeldig om de volgende redenen:\n\n" + "\n".join(f"• {error}" for error in validation_errors),
            "details": details
        }

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint
    GET /api/health
    """
    logging.info('Health check endpoint called')
    
    return func.HttpResponse(
        json.dumps({"status": "healthy", "message": "API is running"}),
        mimetype="application/json",
        status_code=200
    )

@app.route(route="process-attestation", methods=["POST"])
def process_attestation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process attestation file upload
    POST /api/process-attestation
    Accepts file upload and validates the attestation using AI
    """
    logging.info('Process attestation endpoint called')
    
    try:
        # Get the uploaded file
        file = req.files.get('file')
        
        if not file:
            return func.HttpResponse(
                json.dumps({"error": "Geen bestand geüpload"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Read file content
        file_content = file.read()
        file_name = file.filename
        file_size = len(file_content)
        
        logging.info(f"Received file: {file_name}, size: {file_size} bytes")
        
        # Analyze document with Azure Content Understanding
        validation_result = analyze_document_with_content_understanding(file_content, file_name)
        
        # Add file size to details
        if "details" in validation_result:
            validation_result["details"]["Bestandsgrootte"] = f"{file_size / 1024:.2f} KB"
        
        validation_result["timestamp"] = datetime.now().isoformat()
        
        return func.HttpResponse(
            json.dumps(validation_result),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error processing attestation: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Fout bij het verwerken van het bestand",
                "message": str(e)
            }),
            mimetype="application/json",
            status_code=500
        )
