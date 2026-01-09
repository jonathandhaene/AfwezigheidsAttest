"""
Azure Functions App - Python v2 Programming Model
Main entry point for all HTTP-triggered functions
"""

import azure.functions as func
import logging
import json
from datetime import datetime
from controllers.attestation_controller import process_attestation as process_attestation_controller

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


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
        
        # Process attestation through controller (orchestration layer)
        validation_result = process_attestation_controller(file_content, file_name)
        
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
