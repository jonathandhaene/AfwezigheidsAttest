"""
Azure Functions App - Python v2 Programming Model
Main entry point for all HTTP-triggered functions
"""

import azure.functions as func
import logging
import json
from datetime import datetime
from controllers.attestation_controller import process_attestation as process_attestation_controller
from services.message_translations import get_message

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


@app.route(route="auth-check", methods=["GET"])
def auth_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Authentication check endpoint
    GET /api/auth-check
    Verifies if user credentials are available and valid
    """
    logging.info('Authentication check endpoint called')
    
    try:
        from services.credentials_service import is_authenticated
        
        # Check if user is already authenticated without triggering login
        if is_authenticated():
            logging.info('User is authenticated')
            return func.HttpResponse(
                json.dumps({
                    "authenticated": True,
                    "message": "User is authenticated"
                }),
                mimetype="application/json",
                status_code=200
            )
        else:
            logging.info('User is not authenticated')
            return func.HttpResponse(
                json.dumps({
                    "authenticated": False,
                    "message": "Authentication required"
                }),
                mimetype="application/json",
                status_code=200  # Return 200 with authenticated=false (not an error)
            )
            
    except Exception as e:
        logging.error(f"Authentication check failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "authenticated": False,
                "message": "Authentication check failed",
                "error": str(e)
            }),
            mimetype="application/json",
            status_code=200  # Return 200 with authenticated=false
        )


@app.route(route="login", methods=["POST"])
def login(req: func.HttpRequest) -> func.HttpResponse:
    """
    Login endpoint - triggers interactive browser authentication
    POST /api/login
    """
    logging.info('Login endpoint called')
    
    try:
        from services.credentials_service import get_credential, clear_credential
        
        # Clear cached credential to force fresh authentication and avoid state mismatch
        clear_credential()
        
        # Trigger authentication by requesting a token
        credential = get_credential()
        token = credential.get_token("https://database.windows.net/.default")
        
        if token and token.token:
            logging.info('User successfully authenticated')
            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": "Successfully authenticated"
                }),
                mimetype="application/json",
                status_code=200
            )
        else:
            logging.error('Authentication failed - no token received')
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "Authentication failed"
                }),
                mimetype="application/json",
                status_code=401
            )
            
    except Exception as e:
        logging.error(f"Login failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": "Authentication failed",
                "error": str(e)
            }),
            mimetype="application/json",
            status_code=401
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
        
        # Get language from form data (default to 'nl' if not provided)
        language = req.form.get('language', 'nl')
        
        if not file:
            return func.HttpResponse(
                json.dumps({"error": get_message("no_file_uploaded", language)}),
                mimetype="application/json",
                status_code=400
            )
        
        # Read file content
        file_content = file.read()
        file_name = file.filename
        file_size = len(file_content)
        
        logging.info(f"Received file: {file_name}, size: {file_size} bytes, language: {language}")
        
        # Process attestation through controller (orchestration layer)
        validation_result = process_attestation_controller(file_content, file_name, language)
        
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
        # Try to get language, default to 'nl' if not available
        language = req.form.get('language', 'nl') if hasattr(req, 'form') else 'nl'
        return func.HttpResponse(
            json.dumps({
                "error": get_message("file_processing_error", language),
                "message": str(e)
            }),
            mimetype="application/json",
            status_code=500
        )
