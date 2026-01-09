# Code Architecture Documentation

## Overview
The application has been refactored from a monolithic `function_app.py` (480 lines) into a layered architecture with separation of concerns.

## Architecture Layers

### 1. **Presentation Layer** - `function_app.py` (84 lines)
**Purpose**: HTTP endpoint handlers only

**Responsibilities**:
- Route HTTP requests to appropriate business logic
- Handle request/response formatting
- Manage HTTP status codes and error responses

**Endpoints**:
- `GET /api/health` - Health check
- `POST /api/process-attestation` - File upload and validation

**Dependencies**: `document_service`

---

### 2. **Business Logic Layer** - `document_service.py` (210 lines)
**Purpose**: Document analysis, validation, and business rules

**Responsibilities**:
- Orchestrate Content Understanding API calls
- Extract structured fields from AI analysis results
- Implement validation rules (dates, signatures, fraud detection)
- Build validation result messages and details

**Functions**:
- `analyze_document_with_content_understanding()` - Main orchestrator
- `extract_document_info()` - Extract structured fields from AI result
- `validate_attestation()` - Apply business validation rules

**Dependencies**: `content_understanding_client`, `database_service`, `azure.identity`

---

### 3. **Data Access Layer** - `database_service.py` (167 lines)
**Purpose**: SQL Server database interactions

**Responsibilities**:
- Manage database connections with Entra ID authentication
- Execute doctor validation queries
- Implement two-tier search strategy (RIZIV exact match, name+city fuzzy match)
- Detect fraud (no match = fraud)

**Functions**:
- `validate_doctor_in_database()` - Validate doctor against Azure SQL Database

**Dependencies**: `pyodbc`, `struct`, `azure.identity`

---

### 4. **API Integration Layer** - `content_understanding_client.py` (existing)
**Purpose**: Azure Content Understanding API client

**Responsibilities**:
- Handle REST API authentication (API key or Azure AD)
- POST documents to Content Understanding service
- Poll for analysis results
- Manage token refresh

---

## Data Flow

```
1. HTTP Request → function_app.py
   ↓
2. Extract file → Pass to document_service
   ↓
3. Analyze with AI → content_understanding_client
   ↓
4. Extract fields → document_service
   ↓
5. Validate doctor → database_service (SQL)
   ↓
6. Apply business rules → document_service
   ↓
7. Return result → function_app.py
   ↓
8. HTTP Response → Client
```

## Benefits of Refactoring

### 1. **Separation of Concerns**
- Each module has a single, clear responsibility
- Easier to understand and maintain

### 2. **Testability**
- Business logic can be tested independently of HTTP layer
- Database access can be mocked for unit tests
- Clear boundaries between components

### 3. **Reusability**
- `database_service` can be reused by other functions
- Business logic is independent of HTTP framework

### 4. **Maintainability**
- Changes to validation rules don't affect HTTP routing
- Database schema changes isolated to `database_service`
- AI service changes isolated to `content_understanding_client`

### 5. **Readability**
- 84-line HTTP handler is easy to understand
- Business logic is clearly separated from infrastructure code
- File sizes are manageable (84, 210, 167 lines vs 480 lines)

## File Structure

```
api/
├── function_app.py              # HTTP endpoints (84 lines)
├── document_service.py          # Business logic (210 lines)
├── database_service.py          # Data access (167 lines)
├── content_understanding_client.py  # API client (existing)
├── requirements.txt
└── local.settings.json
```

## Import Dependencies

```
function_app.py
└── document_service
    ├── content_understanding_client
    │   └── azure.identity.DefaultAzureCredential
    └── database_service
        └── azure.identity.DefaultAzureCredential
```

No circular dependencies - clean one-way dependency tree.

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
