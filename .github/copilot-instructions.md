# AfwezigheidsAttest - AI Agent Instructions

Medical document validation system with Azure AI and SQL Server using **4-layer clean architecture**.

## Architecture: Critical Rules

**4 Layers** (NO service-to-service calls):
1. **Presentation** (`function_app.py`) → HTTP routes only
2. **Orchestration** (`controllers/attestation_controller.py`) → Coordinates services
3. **Business Logic** (`services/document_service.py`) → Document validation rules
4. **Data Access** (`services/database_service.py`) + Auth (`services/credentials_service.py`)

**Golden Rule**: Services NEVER import other services. Controllers orchestrate everything.

**Visual Architecture**: See `ARCHITECTURE_DIAGRAM.md` for layer diagrams and call flow examples.

### 7-Step Controller Workflow

From `attestation_controller.py` (191 lines):
```python
# Step 1: Analyze document with Azure Content Understanding
analysis = analyze_document_with_content_understanding(file_content, file_name)

# Step 2: Extract structured data (16 fields: patient, doctor, dates, etc.)
extracted = extract_document_info(analysis["result"])

# Step 3: Validate business rules (signature, date logic)
validation_errors = validate_attestation_rules(extracted)

# Step 4: Check doctor against SQL database
doctor_check = validate_doctor_in_database(extracted["doctor_info"])

# Step 5: Calculate fraud detection (doctor not found + validation errors)
fraud_detected = doctor_check.get("fraud_detected", False)

# Step 6: Create fraud case if needed (priority formula: signature*50 + doctor*30 + errors*10)
if fraud_detected or validation_errors:
    fraud_case = create_fraud_case(extracted, reason, doctor_check)

# Step 7: Build final result dict (valid, details, error_category, status_code)
return _build_result(extracted, validation_errors, doctor_check, fraud_case_id, file_name)
```

## Quick Start

**Run both frontend + backend**:
```powershell
.\start.ps1  # Opens 2 terminals automatically
```

**Manual start**:
```powershell
# Terminal 1: Backend (must activate venv first)
cd api; .venv\Scripts\Activate.ps1; func start

# Terminal 2: Frontend
cd frontend; npm run dev
```

**VS Code Tasks**: Use "Start Azure Function" + "Start Frontend" from task runner.

**First-time setup**:
1. Copy `api/local.settings.json.example` → `api/local.settings.json`
2. Add Azure Content Understanding credentials (see `SETUP_AZURE_AI.md`)
3. Add SQL Server connection details (see `SETUP_SQL_DATABASE.md`)

## Code Patterns You Must Follow

### Backend: Error Handling Decorator

ALL external service calls use `@handle_service_errors(service_name)`:

```python
from decorators.service_errors import handle_service_errors

@handle_service_errors("Azure Content Understanding")
def call_azure_api(data):
    # Any Azure/requests/pyodbc exception → ServiceCallError
```

Catches: Azure SDK errors, `requests` timeouts, pyodbc connection failures.  
Raises: `ServiceCallError`, `ServiceTimeoutError`, `ServiceConnectionError`.

### Frontend: Mandatory i18n

**NEVER hardcode UI text**. Use translation keys:

```jsx
import { useTranslation } from './i18n'

function MyComponent() {
  const { t } = useTranslation()
  return <h1>{t('app.title')}</h1>  // ✅ Correct
  // return <h1>Welcome</h1>         // ❌ Wrong!
}
```

Add keys to `frontend/src/translations/{nl,fr,en}.json` with nested structure:
```json
{ "results": { "fields": { "name": "Naam" } } }
```

Access: `t('results.fields.name')` or with params: `t('error.message', { code: 500 })`

### Frontend: Fluent UI Overrides

Load order is **critical** (`main.jsx`):
```jsx
import 'bootstrap/dist/css/bootstrap.min.css'  // 1st
import './index.css'                            // 2nd
import './FluentUI.css'                         // 3rd - MUST BE LAST
```

**Design rules** (intentional, don't "fix"):
- No rounded corners: `border-radius: 0 !important` on all cards/alerts
- Use CSS variables: `--fluent-primary`, `--fluent-spacing-m`, `--fluent-elevation-8`
- Override Bootstrap with `!important` when needed

### Backend: Controller Response Format

Controllers return standardized dicts:
```python
{
    "valid": bool,                  # Overall validation result
    "details": {                    # Structured extraction results
        "Patiënt": str,
        "Rijksregisternummer": str,
        # ...16 total fields
    },
    "error_category": str,          # "validation" | "fraud" | "technical"
    "status_code": int              # HTTP code for function_app.py
}
```

This format matches frontend expectations in `App.jsx`.

## Critical Integration Details

**Azure Content Understanding**:
- Endpoint must end with `/` (e.g., `https://name.services.ai.azure.com/`)
- Analyzer ID configured separately (prebuilt model)
- Default timeout: 120s (polling for async analysis)

**SQL Server Auth**:
- Uses `InteractiveBrowserCredential` (cached in `credentials_service.py`)
- Connection string requires `DRIVER={ODBC Driver 18 for SQL Server}`
- Token auto-refreshes via `azure-identity` library

**Fraud Case Creation**:
- Priority formula in `database_service.py`: `(signature_missing * 50) + (doctor_invalid * 30) + (validation_errors * 10)`
- Auto-assigns GUID, timestamp, "Open" status

## File Locations

- **Architecture docs**: `ARCHITECTURE.md` (259 lines), `ARCHITECTURE_DIAGRAM.md` (visual)
- **Setup guides**: `SETUP_AZURE_AI.md`, `SETUP_SQL_DATABASE.md`
- **Error handling**: `api/decorators/service_errors.py` (165 lines)
- **Main workflow**: `api/controllers/attestation_controller.py` (191 lines, 7-step process)
- **i18n system**: `frontend/src/i18n.jsx` (localStorage-backed)
- **Fluent UI**: `frontend/src/FluentUI.css` (696 lines of overrides)

## Testing Patterns

**Frontend Tests** (Vitest):
```bash
cd frontend
npm run test
```

**Test Structure Pattern**:
```jsx
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { LanguageProvider } from './i18n'

describe('Component', () => {
  it('renders with translation', () => {
    const { getByText } = render(
      <LanguageProvider><Component /></LanguageProvider>
    )
    expect(getByText(/expected text/i)).toBeInTheDocument()
  })
})
```

**Backend Tests**: No unit test suite yet. Test manually:
1. Upload test PDF via frontend
2. Check Azure Function logs in terminal
3. Verify fraud case in SQL database
4. Validate response structure matches controller format

## Debugging Guide

### Backend Issues

**Azure Function won't start**:
```powershell
# Check venv activation
cd api
.venv\Scripts\Activate.ps1

# Verify dependencies
pip list | Select-String "azure"

# Check local settings
cat local.settings.json  # Must have AZURE_CONTENT_UNDERSTANDING_* and SQL_*
```

**"Module not found" errors**:
- Ensure you're in activated venv (`(.venv)` in prompt)
- Run `pip install -r requirements.txt` in `api/` directory
- Restart VS Code terminal after installing packages

**Azure Content Understanding timeouts**:
- Default timeout: 120s (configured in `document_service.py`)
- Check endpoint ends with `/` in `local.settings.json`
- Verify analyzer ID is correct (prebuilt model ID)
- Look for `ServiceTimeoutError` in logs

**SQL connection failures**:
```python
# ServiceConnectionError → Check these:
# 1. ODBC Driver 18 installed? Run: Get-OdbcDriver -Name "ODBC Driver 18 for SQL Server"
# 2. Server name format: "name.database.windows.net" (no prefix)
# 3. Azure AD token refresh: Delete cached credential, restart function
```

**CORS errors** (frontend can't call API):
- Frontend expects API at `/api/*` (proxied by Vite)
- Check `frontend/vite.config.js` has proxy configuration
- Backend must run on `localhost:7071` (default Azure Functions port)

### Frontend Issues

**Translation key not found**:
```jsx
// Console shows: "Missing translation for: app.newKey"
// Fix: Add to ALL 3 files:
// - frontend/src/translations/nl.json
// - frontend/src/translations/fr.json
// - frontend/src/translations/en.json
```

**Fluent UI styles broken**:
```jsx
// Check main.jsx load order (THIS EXACT ORDER):
import 'bootstrap/dist/css/bootstrap.min.css'  // 1st
import './index.css'                            // 2nd
import './FluentUI.css'                         // 3rd - overrides everything
```

**Language not persisting**:
- Check browser localStorage: `localStorage.getItem('language')`
- Clear if stuck: `localStorage.removeItem('language')`
- Defaults to Dutch (nl) if not set

### Common Log Messages

```python
# ✅ Success indicators:
"InteractiveBrowserCredential.get_token succeeded"  # SQL auth working
"Analysis completed after X.XX seconds"              # AI analysis done
"Doctor verified by RIZIV: X-XXXXX-XX-XXX"          # Doctor found in DB
"Fraud case created successfully: <guid>"            # Case logged

# ⚠️ Warning signs:
"Doctor not found in database"                       # Triggers fraud case
"Signature not detected"                             # Validation error
"Date validation failed"                             # Business rule broken

# ❌ Error indicators:
"Azure Content Understanding connection failed"      # Check endpoint/key
"Failed to connect to SQL Server"                    # Check connection string
"Service call timed out after 120 seconds"          # Network/Azure issue
```

## Deployment

**Azure Developer CLI (azd)**:
```bash
# Initialize (first time)
azd init

# Provision Azure resources (Static Web App + Function App)
azd provision

# Deploy code
azd deploy

# Both provision + deploy
azd up
```

**Infrastructure as Code**:
- `infra/main.bicep` - Bicep template for Azure resources
- `azure.yaml` - azd configuration (frontend: Static Web App, api: Function App)

**Environment Configuration**:
```bash
# Set secrets in Azure (not in local.settings.json)
azd env set AZURE_CONTENT_UNDERSTANDING_ENDPOINT "https://..."
azd env set AZURE_CONTENT_UNDERSTANDING_KEY "..."
azd env set SQL_SERVER "name.database.windows.net"
azd env set SQL_DATABASE "dbname"
```

**Manual Deployment** (alternative):
1. **Frontend**: `cd frontend; npm run build; # Upload dist/ to Azure Static Web App`
2. **Backend**: `cd api; func azure functionapp publish <function-app-name>`

**Post-Deployment Checks**:
- Verify Static Web App URL in Azure Portal
- Test `/api/health` endpoint (should return `{"status": "healthy"}`)
- Check Function App logs for startup errors
- Ensure CORS allows Static Web App domain

## Data Flow

**Request Flow** (see `ARCHITECTURE_DIAGRAM.md` for visual):
```
User uploads PDF
  ↓ HTTP POST /api/process-attestation
function_app.py (Presentation)
  ↓ process_attestation(file, name)
attestation_controller.py (Orchestration)
  ↓ 7-step workflow
  ├─ document_service.py → Azure Content Understanding API
  ├─ database_service.py → Azure SQL Database
  └─ credentials_service.py (shared auth)
  ↓ Returns JSON
Frontend displays results in Fluent UI cards
```

**Database Schema**:
- `doctors_riziv` table: RIZIV number, name, address, city (validation source)
- `fraud_cases` table: GUID, patient, doctor, reason, priority, status, timestamp

## Common Mistakes

❌ **Don't**:
- Import services into other services (breaks architecture)
- Hardcode UI strings (breaks i18n)
- Add `border-radius` to Fluent UI components (intentionally flat)
- Forget to activate Python venv before `func start`
- Use `!important` everywhere (only for Bootstrap overrides)
- Commit `local.settings.json` (has secrets, gitignored)
- Deploy without setting Azure environment variables

✅ **Do**:
- Put all service coordination logic in controllers
- Add translations to all 3 language files (`nl`/`fr`/`en`)
- Preserve CSS load order (Bootstrap → index.css → FluentUI.css)
- Use `@handle_service_errors` for all external calls
- Check `local.settings.json.example` for required config keys
- Test locally before deploying (`.\start.ps1`)
- Review `ARCHITECTURE_DIAGRAM.md` for workflow understanding
