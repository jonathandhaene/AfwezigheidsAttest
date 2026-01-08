"""
Azure Functions App - Python v2 Programming Model
Main entry point for all HTTP-triggered functions
"""

import azure.functions as func
import logging
import json
import os
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

def extract_document_info(result: dict) -> dict:
    """
    Extract relevant information from Content Understanding result
    """
    extracted_data = {
        "dates": [],
        "has_signature": False,
        "text_content": ""
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
        
        logging.info(f"Extracted {len(extracted_data['dates'])} date references, signature: {extracted_data['has_signature']}")
        
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

@app.route(route="attestation", methods=["GET", "POST"])
def attestation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Attestation endpoint - Handle absence attestations
    GET /api/attestation - Retrieve attestations
    POST /api/attestation - Create new attestation
    """
    logging.info('Attestation endpoint called')
    
    if req.method == "GET":
        # TODO: Implement GET logic to retrieve attestations
        return func.HttpResponse(
            json.dumps({"attestations": []}),
            mimetype="application/json",
            status_code=200
        )
    
    elif req.method == "POST":
        try:
            req_body = req.get_json()
            # TODO: Implement POST logic to create attestation
            logging.info(f"Received attestation request: {req_body}")
            
            return func.HttpResponse(
                json.dumps({"message": "Attestation created", "id": "123"}),
                mimetype="application/json",
                status_code=201
            )
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON"}),
                mimetype="application/json",
                status_code=400
            )
