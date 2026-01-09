# Architecture Diagram

## Layer Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT (React Frontend)                      │
│                         localhost:5173                               │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP POST /api/process-attestation
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: PRESENTATION (HTTP)                      │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ function_app.py (86 lines)                                   │   │
│  │ • Handles HTTP requests/responses                            │   │
│  │ • Routes to controller                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ process_attestation(file, name)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│               LAYER 2: ORCHESTRATION (CONTROLLER)                    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ controllers/attestation_controller.py (190 lines)           │   │
│  │ • Orchestrates workflow                                      │   │
│  │ • Coordinates service calls                                  │   │
│  │ • Builds final responses                                     │   │
│  │ • NO service-to-service calls                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──┬────────────────┬─────────────────┬────────────────┬──────────────┘
   │ Step 1         │ Step 2          │ Step 3         │ Step 4-5
   │ analyze()      │ extract()       │ validate()     │ validate_doctor()
   │                │                 │                │ create_fraud_case()
   ▼                ▼                 ▼                ▼
┌──────────────────────────────┐  ┌──────────────────────────────────┐
│ LAYER 3: BUSINESS LOGIC      │  │ LAYER 3: DATA ACCESS             │
│                               │  │                                  │
│ ┌───────────────────────────┐ │  │ ┌──────────────────────────────┐│
│ │services/document_service │ │  │ │services/database_service     ││
│ │(218 lines)               │ │  │ │(276 lines)                   ││
│ │                           │ │  │ │                              ││
│ │• AI analysis             │ │  │ │• Doctor validation           ││
│ │• Data extraction         │ │  │ │• Fraud case creation         ││
│ │• Business rules          │ │  │ │• SQL operations              ││
│ │• NO database calls       │ │  │ │                              ││
│ └───────────────────────────┘ │  │ └──────────────────────────────┘│
└───┬─────────────────────────┘  └────────────┬─────────────────────┘
    │                                           │
    │ Uses credentials                          │ Uses credentials
    ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│          LAYER 4: AUTHENTICATION (SHARED UTILITIES)                  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ services/credentials_service.py (37 lines)                   │   │
│  │ • Single cached credential                                   │   │
│  │ • SQL token generation                                       │   │
│  │ • Eliminates multiple logins                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
    │                                           │
    │ Auth to AI Service                        │ Auth to SQL Server
    ▼                                           ▼
┌──────────────────────────┐          ┌───────────────────────────┐
│ Azure Content            │          │ Azure SQL Database        │
│ Understanding API        │          │ • doctors_riziv table     │
│ (2025-11-01)             │          │ • fraud_cases table       │
└──────────────────────────┘          └───────────────────────────┘
```

## Call Flow Example

### Scenario: User uploads invalid attestation (missing signature)

```
1. POST /api/process-attestation
   ↓
2. function_app.py receives request
   ↓ calls
3. controllers/attestation_controller.process_attestation()
   │
   ├─→ Step 1: services/document_service.analyze_document()
   │   └─→ Calls Azure Content Understanding API
   │   └─→ Returns: {success: true, result: {...}}
   │
   ├─→ Step 2: services/document_service.extract_document_info(result)
   │   └─→ Extracts 16+ fields from API response
   │   └─→ Returns: extracted_data dict
   │
   ├─→ Step 3: services/document_service.validate_attestation_rules(data)
   │   └─→ Checks dates, signature
   │   └─→ Returns: ["Er ontbreekt een handtekening..."]
   │
   ├─→ Step 4: services/database_service.validate_doctor_in_database(doctor_info)
   │   └─→ Queries Azure SQL Database
   │   └─→ Returns: {doctor_found: true, fraud_detected: false}
   │
   ├─→ Step 5: services/database_service.create_fraud_case(data, reason, validation)
   │   └─→ INSERT into fraud_cases table
   │   └─→ Returns: {success: true, case_id: "guid"}
   │
   └─→ Step 6: controller._build_result()
       └─→ Combines all data into final response
       └─→ Returns: {valid: false, message: "...", details: {...}}
   ↓
4. function_app.py formats HTTP response
   ↓
5. JSON response to React frontend
```

## Key Architecture Features

### ✅ Separation of Concerns
- **function_app**: HTTP only
- **controller**: Orchestration only  
- **services**: Domain logic only

### ✅ No Service-to-Service Calls
```
❌ BEFORE: document_service → database_service (tight coupling)
✅ AFTER:  controller → document_service
                     → database_service (loose coupling)
```

### ✅ Testability
```python
# Unit test document_service (no mocking needed)
def test_validate_rules():
    data = {"has_signature": False, ...}
    errors = validate_attestation_rules(data)
    assert "handtekening" in errors[0]

# Unit test controller with mocked services
def test_controller(mock_doc_service, mock_db_service):
    mock_doc_service.analyze.return_value = {...}
    result = process_attestation(file, name)
    assert result["valid"] == False
```

### ✅ Reusability
- Services can be used by different controllers
- Controller can orchestrate different workflows
- Easy to add new business processes

## Dependency Graph

```
function_app.py
    └── controllers/attestation_controller.py
            ├── services/document_service.py
            │       ├── content_understanding_client.py
            │       └── services/credentials_service.py
            └── services/database_service.py
                    └── services/credentials_service.py

NO CIRCULAR DEPENDENCIES ✅
NO SERVICE-TO-SERVICE CALLS ✅
```

## File Sizes

```
function_app.py                          86 lines   ▓░░░░░░░░░░░
controllers/attestation_controller.py   190 lines   ▓▓▓▓▓░░░░░░░
services/document_service.py            218 lines   ▓▓▓▓▓▓░░░░░░
services/database_service.py            276 lines   ▓▓▓▓▓▓▓▓░░░░
services/credentials_service.py          37 lines   ▓░░░░░░░░░░░

Total: 807 lines (was 480 lines in monolith)
Maintainability: HIGH ✅
Testability: HIGH ✅
Coupling: LOW ✅
```
