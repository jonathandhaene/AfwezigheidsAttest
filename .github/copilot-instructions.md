# AfwezigheidsAttest - AI Agent Instructions

## Architecture Overview

This is a medical document validation system using **4-layer clean architecture** with Azure AI and SQL Server.

### Layer Structure (Critical: No service-to-service calls)
1. **Presentation** (`function_app.py`) - HTTP endpoints only
2. **Orchestration** (`controllers/`) - Workflow coordination, calls multiple services
3. **Business Logic** (`services/document_service.py`) - Document analysis, validation rules
4. **Data Access** (`services/database_service.py`) - SQL queries, fraud case creation
5. **Auth** (`services/credentials_service.py`) - Cached Azure AD credential singleton

**Key Rule**: Services NEVER call other services. Only controllers orchestrate service calls.

### Tech Stack
- **Frontend**: React 18 + Vite, Bootstrap 5, Microsoft Fluent UI Design System
- **Backend**: Azure Functions Python v2 (isolated model)
- **AI**: Azure Content Understanding (document analysis)
- **Database**: SQL Server with Entra ID authentication
- **I18N**: Custom provider supporting Dutch (nl), French (fr), English (en)

## Development Workflow

### Local Development (PowerShell)
```powershell
# Start both frontend and backend in separate terminals
.\start.ps1

# Or manually:
# Terminal 1 - Backend
cd api; func start

# Terminal 2 - Frontend  
cd frontend; npm run dev
```

**URLs**:
- Frontend: http://localhost:5173/
- Backend: http://localhost:7071/api/

### Python Virtual Environment
Always activate before Python work:
```powershell
cd api
.venv\Scripts\Activate.ps1
```

## Code Conventions

### Backend: Decorator Pattern for Error Handling
All service calls use `@handle_service_errors(service_name)` decorator:
```python
from decorators.service_errors import handle_service_errors

@handle_service_errors("Azure Content Understanding")
def analyze_document(file_content):
    # Service call logic
```

Raises: `ServiceCallError`, `ServiceTimeoutError`, `ServiceConnectionError`

### Frontend: Fluent UI Design System
- **CSS**: `FluentUI.css` loaded after Bootstrap (load order critical!)
- **Colors**: Use CSS variables: `--fluent-primary` (#0078d4), `--fluent-neutral-*`
- **No rounded corners**: All cards/alerts have `border-radius: 0 !important`
- **Typography**: Segoe UI font family throughout
- **Spacing**: 4px-based scale: `--fluent-spacing-{xs,s,m,l,xl,xxl,xxxl}`
- **Shadows**: Fluent elevation system: `--fluent-elevation-{4,8,16,64}`

### Frontend: Multilingual Support
Use translation hook, NOT hardcoded strings:
```jsx
import { useTranslation } from './i18n'

function MyComponent() {
  const { t } = useTranslation()
  return <h1>{t('app.title')}</h1>
}
```

Translation keys in `frontend/src/translations/{nl,fr,en}.json` use nested structure:
```json
{
  "results": {
    "fields": {
      "name": "Naam"
    }
  }
}
```

Access: `t('results.fields.name')`

### Frontend: Responsive Grid Layout
Result cards use Bootstrap responsive columns:
- **Full width**: `col-12` (File Info, Other Info)
- **Half width**: `col-md-6` (Patient, Doctor, Attestation, Summary)
- Cards stack vertically on mobile, 2-per-row on ≥768px screens

### Backend: Controller Return Structure
Controllers return dicts with specific structure:
```python
{
    "valid": bool,
    "details": {
        "Patiënt": str,
        "Rijksregisternummer": str,
        # ... structured fields
    },
    "error_category": str,  # "validation" | "fraud" | "technical"
    "status_code": int
}
```

## Critical Integration Points

### Azure Content Understanding API
- Client: `content_understanding_client.py`
- Requires: `AZURE_CONTENT_UNDERSTANDING_ENDPOINT` and `AZURE_CONTENT_UNDERSTANDING_KEY`
- Returns: Prebuilt document analysis results
- Timeout: 120 seconds default

### SQL Server Authentication
- Uses **Azure AD Interactive Browser** flow via cached credential
- Token refresh handled automatically by `credentials_service`
- Connection string format: `DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;Encrypt=yes;TrustServerCertificate=no`

### Environment Configuration
Backend: `api/local.settings.json` (gitignored, use `.example` as template)
```json
{
  "Values": {
    "AZURE_CONTENT_UNDERSTANDING_ENDPOINT": "...",
    "AZURE_CONTENT_UNDERSTANDING_KEY": "...",
    "SQL_CONNECTION_STRING": "..."
  }
}
```

## Key Files Reference

- `ARCHITECTURE.md` - Detailed layer responsibilities and workflow
- `api/decorators/service_errors.py` - Reusable error handling pattern
- `frontend/src/FluentUI.css` - Complete Fluent Design System implementation
- `frontend/src/i18n.jsx` - Translation provider and hook
- `start.ps1` - Multi-terminal development startup script

## Testing & Validation

- Frontend uses **Vitest**: `npm run test`
- Backend decorators tested in production workflows (no unit test suite yet)
- Manual testing workflow: Upload medical attestation PDF → View validation results

## Common Pitfalls

1. **Don't** call services from other services - only controllers orchestrate
2. **Don't** use rounded corners on Fluent UI components (intentionally removed)
3. **Don't** hardcode strings - always use translation keys
4. **Don't** forget to activate Python venv before running functions
5. **Do** use `!important` in FluentUI.css to override Bootstrap defaults
6. **Do** preserve CSS load order: Bootstrap → index.css → FluentUI.css
