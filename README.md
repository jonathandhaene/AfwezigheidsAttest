# AfwezigheidsAttest

Azure-based web application with Python Azure Functions backend.

## Project Structure

```
AfwezigheidsAttest/
├── frontend/               # Static Web App frontend
│   ├── src/               # Source files
│   ├── public/            # Static assets
│   ├── dist/              # Build output
│   └── package.json       # Frontend dependencies
├── api/                   # Python Azure Functions
│   ├── function_app.py    # Main function app entry
│   ├── host.json          # Function host configuration
│   ├── local.settings.json # Local development settings
│   └── requirements.txt   # Python dependencies
├── shared/                # Shared code between frontend and backend
├── tests/                 # Test files
└── infra/                 # Infrastructure as Code (Bicep/Terraform)
```

## Prerequisites

- Node.js (v18 or later)
- Python 3.9 or later
- Azure Functions Core Tools v4
- Azure Static Web Apps CLI
- Azure CLI

## Local Development

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Azure Functions API
```bash
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
func start
```

### Running with SWA CLI
```bash
npx swa start ./frontend/dist --api-location ./api
```

## Deployment

Deploy to Azure using:
```bash
npx swa deploy --env production
```

## Configuration

- Frontend configuration: `frontend/package.json`
- Function configuration: `api/host.json`
- Local settings: `api/local.settings.json` (not committed to git)
