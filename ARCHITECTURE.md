# Code Architecture Documentation

## Overview
The application follows a clean 4-layer architecture with clear separation of concerns and no direct service-to-service coupling.

## Architecture Layers

### 1. **Presentation Layer** - `function_app.py` (86 lines)
**Purpose**: HTTP endpoint handlers only

**Responsibilities**:
- Route HTTP requests
- Handle request/response formatting
- Manage HTTP status codes and error responses
- Delegate processing to controller layer

**Endpoints**:
- `GET /api/health` - Health check
- `POST /api/process-attestation` - File upload and validation

**Dependencies**: `controllers.attestation_controller`

---

### 2. **Orchestration Layer** - `controllers/attestation_controller.py` (190 lines)
**Purpose**: Workflow coordination without service-to-service coupling

**Responsibilities**:
- Orchestrate complete attestation processing workflow
- Coordinate calls between services
- Handle business logic flow decisions
- Build final response structures
- No direct service-to-service calls

**Workflow Steps**:
1. Analyze document (calls document_service)
2. Extract structured data (calls document_service)
3. Validate business rules (calls document_service)
4. Validate doctor in database (calls database_service)
5. Create fraud case if needed (calls database_service)
6. Build and return final result

**Key Functions**:
- `process_attestation()` - Main workflow orchestrator
- `_build_result()` - Result construction logic

**Dependencies**: `services.document_service`, `services.database_service`

---

### 3. **Business Logic Layer** - `services/document_service.py` (218 lines)
**Purpose**: Document analysis and business rule validation

**Responsibilities**:
- Orchestrate Content Understanding API calls
- Extract structured fields from AI analysis results
- Validate business rules (dates, signatures) **without** external dependencies
- Return data structures (not final responses)

**Key Functions**:
- `analyze_document_with_content_understanding()` - Call AI service, return result
- `extract_document_info()` - Extract fields from AI result
- `validate_attestation_rules()` - Validate dates/signature, return error list

**Dependencies**: `content_understanding_client`, `services.credentials_service`
**No longer calls**: `database_service` (moved to controller)

---

### 4. **Data Access Layer** - `services/database_service.py` (276 lines)
**Purpose**: SQL Server database interactions and fraud case management

**Responsibilities**:
- Manage database connections with Entra ID authentication
- Execute doctor validation queries
- Create fraud cases in database
- Return validation results (not full responses)

**Functions**:
- `validate_doctor_in_database()` - Validate doctor, return validation dict
- `create_fraud_case()` - Insert fraud case, return case_id

**Dependencies**: `services.credentials_service`

---

### 5. **Authentication Layer** - `services/credentials_service.py` (37 lines)
**Purpose**: Centralized credential management

**Responsibilities**:
- Provide single cached Azure AD credential
- Generate SQL authentication tokens
- Eliminate multiple login prompts

**Functions**:
- `get_credential()` - Returns cached InteractiveBrowserCredential
- `get_sql_token_struct()` - Returns formatted SQL token

**Dependencies**: `azure.identity`

---

## Data Flow

```
1. HTTP Request 
   ↓
2. function_app.py (HTTP layer)
   ↓
3. attestation_controller.py (Orchestration) ──→ Coordinates workflow
   ├─→ document_service.analyze_document()
   ├─→ document_service.extract_document_info()
   ├─→ document_service.validate_attestation_rules()
   ├─→ database_service.validate_doctor_in_database()
   ├─→ database_service.create_fraud_case() [if needed]
   └─→ Build final result
   ↓
4. HTTP Response
   ↓
5. Client (React frontend)
```

## Key Architectural Principles

### 1. **No Service-to-Service Calls**
- ✅ Services do NOT call other services
- ✅ Controller orchestrates all service interactions
- ✅ Clear dependency flow: Controller → Services
- ✅ Services are independent and reusable

### 2. **Single Responsibility**
- **function_app**: HTTP only
- **controller**: Workflow orchestration only
- **document_service**: AI analysis and business rules only
- **database_service**: Data persistence only
- **credentials_service**: Authentication only

### 3. **Testability**
- Each service can be unit tested independently
- Controller can be tested with mocked services
- No complex service mocking chains required

### 4. **Reusability**
- Services can be used by different controllers
- No coupling between business logic and orchestration
- Easy to add new workflows

---

## Benefits of This Architecture

### Before (3-layer with service coupling):
```
function_app → document_service → database_service
                     ↓
              (builds responses, creates fraud cases)
```
**Problems**:
- ❌ document_service had too many responsibilities
- ❌ Services calling services (tight coupling)
- ❌ Hard to test in isolation
- ❌ Business logic mixed with orchestration

### After (4-layer with controller):
```
function_app → attestation_controller → document_service
                         ↓              → database_service
                   (orchestration)
```
**Improvements**:
- ✅ Clear separation of orchestration and business logic
- ✅ No service-to-service calls
- ✅ Easy to test each layer independently
- ✅ Easy to add new workflows or reuse services
- ✅ Controller handles all coordination logic

---

## File Structure

```
api/
├── function_app.py                          # HTTP layer (86 lines)
├── controllers/
│   └── attestation_controller.py            # Orchestration layer (190 lines)
├── services/
│   ├── document_service.py                  # Business logic (218 lines)
│   ├── database_service.py                  # Data access (276 lines)
│   └── credentials_service.py               # Authentication (37 lines)
├── content_understanding_client.py          # External API client
├── requirements.txt
└── local.settings.json
```

## Import Dependencies

```
function_app.py
└── controllers.attestation_controller
    ├── services.document_service
    │   ├── content_understanding_client
    │   │   └── services.credentials_service
    │   └── services.credentials_service
    └── services.database_service
        └── services.credentials_service
```

**Clean one-way dependency tree** - no circular dependencies, no service-to-service calls.

---

## Testing Strategy

### Unit Tests
- **document_service**: Test validation logic with mocked database and AI results
- **database_service**: Test SQL queries with test database or mocks
- **content_understanding_client**: Test API calls with mocked HTTP responses

### Integration Tests
- Test full flow from HTTP request to response
- Use test documents with known results
- Verify fraud detection with test database

### End-to-End Tests
- Test with real Azure services
- Verify Entra ID authentication
- Test with various document types

## Future Enhancements

### Potential Additions
1. **Logging Service**: Centralized logging with structured data
2. **Configuration Service**: Centralized config management
3. **Caching Layer**: Cache doctor lookups to reduce database load
4. **Metrics Service**: Track validation rates, fraud detection stats
5. **Notification Service**: Alert administrators of fraud attempts

### Scalability
- Each layer can be scaled independently
- Business logic can be moved to separate service if needed
- Database layer can implement connection pooling

## Migration Notes

### Before Refactoring
- Single file: `function_app.py` (480 lines)
- Mixed concerns: HTTP, business logic, database access, AI integration
- Difficult to test individual components

### After Refactoring
- Four modules with clear boundaries
- Each module <250 lines
- Testable, maintainable, extensible

### Compatibility
- No breaking changes to API endpoints
- Same functionality, cleaner code
- All environment variables unchanged
