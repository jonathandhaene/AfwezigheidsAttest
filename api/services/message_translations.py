"""
Message Translations for Backend Services
Provides multilingual support for user-facing messages
"""

MESSAGES = {
    # Doctor validation messages
    "doctor_verified_riziv": {
        "nl": "Arts geverifieerd via RIZIV nummer: {riziv}",
        "fr": "Médecin vérifié via numéro INAMI: {riziv}",
        "en": "Doctor verified via RIZIV number: {riziv}"
    },
    "doctor_verified_name_city": {
        "nl": "Arts geverifieerd via naam en stad: {name}",
        "fr": "Médecin vérifié via nom et ville: {name}",
        "en": "Doctor verified via name and city: {name}"
    },
    "doctor_verified_name": {
        "nl": "Arts geverifieerd via naam: {name}",
        "fr": "Médecin vérifié via nom: {name}",
        "en": "Doctor verified via name: {name}"
    },
    "fraud_detected": {
        "nl": "⚠️ FRAUDE GEDETECTEERD: Arts niet gevonden in geregistreerde artsendatabase",
        "fr": "⚠️ FRAUDE DÉTECTÉE: Médecin non trouvé dans la base de données des médecins enregistrés",
        "en": "⚠️ FRAUD DETECTED: Doctor not found in registered doctors database"
    },
    "fraud_name_mismatch": {
        "nl": "⚠️ FRAUDE GEDETECTEERD: RIZIV nummer bestaat maar naam komt niet overeen (Document: {doc_name}, Database: {db_name})",
        "fr": "⚠️ FRAUDE DÉTECTÉE: Numéro INAMI existe mais le nom ne correspond pas (Document: {doc_name}, Base de données: {db_name})",
        "en": "⚠️ FRAUD DETECTED: RIZIV number exists but name does not match (Document: {doc_name}, Database: {db_name})"
    },
    "fraud_reason_not_found": {
        "nl": "Arts niet gevonden in geregistreerde artsen database",
        "fr": "Médecin non trouvé dans la base de données des médecins enregistrés",
        "en": "Doctor not found in registered doctors database"
    },
    "fraud_reason_name_mismatch": {
        "nl": "RIZIV nummer geldig maar arts naam komt niet overeen met database",
        "fr": "Numéro INAMI valide mais le nom du médecin ne correspond pas à la base de données",
        "en": "RIZIV number valid but doctor name does not match database"
    },
    
    # Error messages
    "no_file_uploaded": {
        "nl": "Geen bestand geüpload",
        "fr": "Aucun fichier téléchargé",
        "en": "No file uploaded"
    },
    "file_processing_error": {
        "nl": "Fout bij het verwerken van het bestand",
        "fr": "Erreur lors du traitement du fichier",
        "en": "Error processing file"
    },
    "document_analysis_error": {
        "nl": "Fout bij het analyseren van het document",
        "fr": "Erreur lors de l'analyse du document",
        "en": "Error analyzing document"
    },
    "document_processing_error": {
        "nl": "❌ Fout bij het verwerken van het document: {error}",
        "fr": "❌ Erreur lors du traitement du document: {error}",
        "en": "❌ Error processing document: {error}"
    },
    "database_error": {
        "nl": "Database fout: {error}",
        "fr": "Erreur de base de données: {error}",
        "en": "Database error: {error}"
    },
    "validation_error": {
        "nl": "Fout bij validatie: {error}",
        "fr": "Erreur de validation: {error}",
        "en": "Validation error: {error}"
    },
    "fraud_case_creation_error": {
        "nl": "Fout bij aanmaken fraudemelding: {error}",
        "fr": "Erreur lors de la création du cas de fraude: {error}",
        "en": "Error creating fraud case: {error}"
    },
    
    # Field labels
    "not_found": {
        "nl": "Niet gevonden",
        "fr": "Non trouvé",
        "en": "Not found"
    },
    "yes": {
        "nl": "Ja",
        "fr": "Oui",
        "en": "Yes"
    },
    "no": {
        "nl": "Nee",
        "fr": "Non",
        "en": "No"
    },
    
    # Validation error messages
    "validation_signature_missing": {
        "nl": "Er ontbreekt een handtekening van de arts op het document",
        "fr": "La signature du médecin est manquante sur le document",
        "en": "The doctor's signature is missing on the document"
    },
    "validation_start_date_future": {
        "nl": "Onmogelijheid startdatum ligt in de toekomst: {date}",
        "fr": "La date de début d'incapacité est dans le futur: {date}",
        "en": "Incapacity start date is in the future: {date}"
    },
    "validation_cert_date_future": {
        "nl": "Certificaat datum ligt in de toekomst: {date}",
        "fr": "La date du certificat est dans le futur: {date}",
        "en": "Certificate date is in the future: {date}"
    },
    
    # Configuration messages
    "db_config_missing": {
        "nl": "Database configuratie ontbreekt - kan validatie niet uitvoeren",
        "fr": "Configuration de base de données manquante - impossible d'effectuer la validation",
        "en": "Database configuration missing - cannot perform validation"
    },
    "azure_ai_not_configured": {
        "nl": "Azure Content Understanding is niet geconfigureerd. Configureer de omgevingsvariabele AZURE_CONTENT_UNDERSTANDING_ENDPOINT.",
        "fr": "Azure Content Understanding n'est pas configuré. Configurez la variable d'environnement AZURE_CONTENT_UNDERSTANDING_ENDPOINT.",
        "en": "Azure Content Understanding is not configured. Configure the AZURE_CONTENT_UNDERSTANDING_ENDPOINT environment variable."
    },
    "configuration_error": {
        "nl": "Configuratiefout: {error}",
        "fr": "Erreur de configuration: {error}",
        "en": "Configuration error: {error}"
    }
}


def get_message(key: str, language: str = 'nl', **kwargs) -> str:
    """
    Get translated message by key and language
    
    Args:
        key: Message key from MESSAGES dict
        language: Language code (nl/fr/en)
        **kwargs: Format parameters for the message
    
    Returns:
        Translated and formatted message
    """
    # Default to Dutch if language not supported
    if language not in ['nl', 'fr', 'en']:
        language = 'nl'
    
    # Get message template
    message_dict = MESSAGES.get(key, {})
    message_template = message_dict.get(language, message_dict.get('nl', ''))
    
    # Format with provided parameters
    try:
        return message_template.format(**kwargs)
    except KeyError:
        return message_template
