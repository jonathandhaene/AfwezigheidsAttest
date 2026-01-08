"""
Azure Functions App - Python v2 Programming Model
Main entry point for all HTTP-triggered functions
"""

import azure.functions as func
import logging
import json
import os
import pyodbc
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
    """
    validation_result = {
        "is_valid": True,
        "doctor_found": False,
        "fraud_detected": False,
        "message": ""
    }
    
    try:
        # Get SQL Server connection details from environment
        server = os.environ.get("SQL_SERVER")
        database = os.environ.get("SQL_DATABASE")
        username = os.environ.get("SQL_USERNAME")
        password = os.environ.get("SQL_PASSWORD")
        
        if not all([server, database, username, password]):
            logging.warning("SQL Server configuration incomplete")
            validation_result["message"] = "Database configuratie ontbreekt"
            return validation_result
        
        if password == "{your_password}":
            logging.warning("SQL password not configured")
            validation_result["message"] = "Database wachtwoord is niet geconfigureerd"
            return validation_result
        
        # Build connection string
        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            f"Uid={username};"
            f"Pwd={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        logging.info(f"Connecting to SQL Server: {server}")
        
        # Connect to database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Query to check if doctor exists and is valid
        # Adjust table name and columns based on your actual schema
        doctor_name = doctor_info.get("name", "")
        doctor_riziv = doctor_info.get("riziv", "")
        
        if doctor_name:
            query = "SELECT COUNT(*) as count, IsActive, IsFraudulent FROM Doctors WHERE DoctorName = ? OR RIZIVNumber = ?"
            cursor.execute(query, (doctor_name, doctor_riziv))
            row = cursor.fetchone()
            
            if row and row[0] > 0:
                validation_result["doctor_found"] = True
                
                # Check if doctor is flagged for fraud
                if hasattr(row, 'IsFraudulent') and row.IsFraudulent:
                    validation_result["fraud_detected"] = True
                    validation_result["is_valid"] = False
                    validation_result["message"] = f"WAARSCHUWING: Arts '{doctor_name}' staat geregistreerd als frauduleus"
                    logging.warning(f"Fraudulent doctor detected: {doctor_name}")
                elif hasattr(row, 'IsActive') and not row.IsActive:
                    validation_result["is_valid"] = False
                    validation_result["message"] = f"Arts '{doctor_name}' is niet meer actief"
                else:
                    validation_result["message"] = f"Arts '{doctor_name}' is geverifieerd"
            else:
                validation_result["doctor_found"] = False
                validation_result["message"] = f"Arts '{doctor_name}' niet gevonden in database"
                logging.info(f"Doctor not found in database: {doctor_name}")
        
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
    Extract relevant information from Content Understanding result
    """
    extracted_data = {
        "dates": [],
        "has_signature": False,
        "text_content": "",
        "doctor_info": {
            "name": "",
            "riziv": ""
        }
    }
    
    try:
        # Get the analysis result
        analyze_result = result.get("analyzeResult", {})
        
        # Extract text content from all pages
        contents = analyze_result.get("contents", [])
        if contents and len(contents) > 0:
            pages = contents[0].get("pages", [])
            for page in pages:
                lines = page.get("lines", [])
                for line in lines:
                    content = line.get("content", "")
                    extracted_data["text_content"] += content + " "
        
        # Look for date patterns in the text
        text = extracted_data["text_content"].lower()
        
        # Check for common Dutch date keywords
        date_keywords = ["datum", "date", "van", "tot", "vanaf", "t/m", "periode"]
        for keyword in date_keywords:
            if keyword in text:
                # Try to extract dates near these keywords
                # This is a simplified approach - you may want more sophisticated date extraction
                extracted_data["dates"].append({
                    "field": keyword,
                    "value": "Gevonden in document"
                })
        
        # Check for signature indicators
        signature_keywords = ["handtekening", "signature", "getekend", "signed", "ondertekend"]
        for keyword in signature_keywords:
            if keyword in text:
                extracted_data["has_signature"] = True
                break
        
        # Also check for signature field in structured fields if available
        fields = analyze_result.get("fields", {})
        if "Signature" in fields or "Handtekening" in fields:
            extracted_data["has_signature"] = True
        
        # Extract doctor information from text
        # Look for RIZIV number patterns (typically 5 digits followed by 2 digits)
        import re
        riziv_pattern = r'RIZIV[:\s]*([0-9]{5}[-/]?[0-9]{2})'
        riziv_match = re.search(riziv_pattern, extracted_data["text_content"], re.IGNORECASE)
        if riziv_match:
            extracted_data["doctor_info"]["riziv"] = riziv_match.group(1)
        
        # Look for doctor name patterns (Dr., Arts, etc.)
        doctor_pattern = r'(?:Dr\.|Arts|Doctor)[\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        doctor_match = re.search(doctor_pattern, extracted_data["text_content"])
        if doctor_match:
            extracted_data["doctor_info"]["name"] = doctor_match.group(1)
        
        logging.info(f"Extracted {len(extracted_data['dates'])} date references, signature: {extracted_data['has_signature']}, doctor: {extracted_data['doctor_info']['name']}")
        
    except Exception as e:
        logging.error(f"Error extracting document info: {str(e)}")
    
    return extracted_data

def validate_attestation(extracted_data: dict, file_name: str) -> dict:
    """
    Validate the attestation based on extracted data
    """
    today = date.today()
    validation_errors = []
    future_dates = []
    
    # Check for future dates in the extracted text
    # Try to find and parse actual dates from the text
    text_words = extracted_data["text_content"].split()
    for i, word in enumerate(text_words):
        try:
            # Try to parse potential date strings
            if len(word) >= 8 and any(char.isdigit() for char in word):
                parsed_date = parser.parse(word, dayfirst=True, fuzzy=True)
                
                # Only consider dates that seem realistic (not year 0, etc.)
                if 2020 <= parsed_date.year <= 2030 and parsed_date.date() > today:
                    future_dates.append({
                        "date": parsed_date.strftime("%d-%m-%Y")
                    })
                    validation_errors.append(
                        f"Het document bevat een toekomstige datum: {parsed_date.strftime('%d-%m-%Y')}"
                    )
        except (ValueError, TypeError, parser.ParserError):
            continue
    
    # Check for signature
    if not extracted_data["has_signature"]:
        validation_errors.append("Er ontbreekt een handtekening op het document")
    
    # Validate doctor information in database
    doctor_validation = validate_doctor_in_database(extracted_data.get("doctor_info", {}))
    if not doctor_validation["is_valid"]:
        validation_errors.append(doctor_validation["message"])
    
    if doctor_validation["fraud_detected"]:
        # Fraud detected - mark as invalid immediately
        return {
            "valid": False,
            "message": "⚠ FRAUDE GEDETECTEERD - Dit attest is afgewezen!",
            "details": {
                "Bestandsnaam": file_name,
                "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "Status": "AFGEWEZEN - FRAUDE",
                "Reden": doctor_validation["message"],
                "Fouten": validation_errors
            }
        }
    
    # Determine if valid
    is_valid = len(validation_errors) == 0
    
    # Build result
    if is_valid:
        return {
            "valid": True,
            "message": "✓ Uw afwezigheidsattest is geldig en geaccepteerd.",
            "details": {
                "Bestandsnaam": file_name,
                "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "Status": "Goedgekeurd",
                "Handtekening aanwezig": "Ja"
            }
        }
    else:
        return {
            "valid": False,
            "message": "✗ Uw afwezigheidsattest is ongeldig om de volgende redenen:\n\n" + "\n".join(f"• {error}" for error in validation_errors),
            "details": {
                "Bestandsnaam": file_name,
                "Verwerkt op": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "Status": "Afgekeurd",
                "Aantal fouten": len(validation_errors),
                "Handtekening aanwezig": "Ja" if extracted_data["has_signature"] else "Nee",
                "Toekomstige datums gevonden": len(future_dates)
            }
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
