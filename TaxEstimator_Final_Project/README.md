# Tax Estimator GenAI Widget

Angular widget + Python API demo for a codeathon project: users ask a natural-language U.S. federal income tax or sales/use tax question, the backend uses Azure OpenAI to extract structured JSON when configured, runs a swappable Python tax calculation engine, and returns a GenAI-style summary.

> Demo only: this is not tax, legal, or accounting advice. Federal constants are based on IRS 2025 brackets/standard deduction references. Sales/use tax rates are sample demo rates and should be replaced with a tax-rate provider or validated jurisdiction tables.

## What This Builds

- Angular standalone widget frontend
- FastAPI backend
- Azure OpenAI GPT-4.5 structured JSON extraction, with regex fallback
- Separate Python tax calculation engine in `backend/app/tax_engine.py`
- Optional Azure OpenAI GPT-4.5 summary generation
- Optional MongoDB persistence
- Optional Azure Blob Storage audit export
- Azure DevOps pipeline starter file

## Codeathon Guides

- [BEGINNER_STEP_BY_STEP_GUIDE.md](docs/BEGINNER_STEP_BY_STEP_GUIDE.md): full setup guide for beginners
- [CODEATHON_PLAYBOOK.md](docs/CODEATHON_PLAYBOOK.md): 16-hour team plan and judging story
- [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md): architecture, files, API contract, and modification guide
- [END_USER_GUIDE.md](docs/END_USER_GUIDE.md): simple usage guide for demo users
- [docs/Tax_Estimator_Step_By_Step_Guide.docx](docs/Tax_Estimator_Step_By_Step_Guide.docx): Word document with setup steps and source code appendix

## Fastest Local Start

From the project root, open two PowerShell terminals.

Terminal 1:

```powershell
.\start-backend.ps1
```

Terminal 2:

```powershell
.\start-frontend.ps1
```

Then open:

```text
http://localhost:4200
```

## Project Structure

```text
tax-estimator-widget/
  backend/
    app/
      main.py                # FastAPI routes
      models.py              # Request/response schemas
      nl_parser.py           # GenAI JSON extraction, with regex fallback
      summary_service.py     # Azure OpenAI summary, with local fallback
      tax_engine.py          # Replaceable tax calculation function
      storage_service.py     # MongoDB + Azure Blob optional persistence
    data/
      sales_tax_rates.json   # Demo sales/use tax table
    requirements.txt
    .env.example
  frontend/
    package.json
    angular.json
    src/
      main.ts
      styles.css
      app/
        app.component.ts
        tax-widget.component.ts
        tax-api.service.ts
        tax.models.ts
  azure-pipelines.yml
```

## Requirements

- Python 3.11+
- Node.js 20+ and npm 10+
- Optional: MongoDB connection string
- Optional: Azure OpenAI resource with a GPT-4.5 deployment
- Optional: Azure Storage account/container

New to the stack? Follow the beginner walkthrough first:

[BEGINNER_STEP_BY_STEP_GUIDE.md](docs/BEGINNER_STEP_BY_STEP_GUIDE.md)

## Run Locally

### 1. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

### 2. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm start
```

Then open:

```text
http://localhost:4200
```

## Example Natural-Language Prompts

```text
Estimate federal tax for single filer earning $120,000 with $5,000 credits.
```

```text
I am married filing jointly, income is $210k, itemized deductions are $40k, credits $2,000.
```

```text
Sales tax for a $2,500 laptop shipped to California.
```

```text
Use tax estimate for $900 purchase in New York.
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env`.

```text
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4.5
AZURE_OPENAI_API_VERSION=2024-10-21

MONGODB_URI=
MONGODB_DATABASE=tax_estimator
MONGODB_COLLECTION=estimates

AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=tax-estimates
```

If Azure OpenAI is not configured, the API uses regex parsing and returns a deterministic local summary so the demo still works.

## API

### `POST /api/estimate`

Request:

```json
{
  "query": "Estimate federal tax for single filer earning $120,000 with $5,000 credits.",
  "save": true
}
```

Response includes:

- `parsed_input`: extracted filing status, income, state, purchase amount, etc.
- `estimate`: calculated tax details
- `summary`: Azure OpenAI or local generated explanation
- `disclaimer`: demo limitation text

## GenAI Boundary

The prototype uses GenAI for language tasks:

- Convert natural-language tax questions into structured JSON
- Explain the deterministic result in business-friendly language

The prototype does not use GenAI to do tax arithmetic. Tax math stays in:

[backend/app/tax_engine.py](backend/app/tax_engine.py)

## Swapping Tax Logic

The core tax function is deliberately isolated:

[backend/app/tax_engine.py](backend/app/tax_engine.py)

Main entry point:

```python
def estimate_tax(parsed: ParsedTaxInput, rates_path: Path | None = None) -> TaxEstimate:
```

During the codeathon, your tax team can replace this file with:

- a real federal tax library
- tax vendor API calls
- CSV/JSON-backed jurisdiction rates
- more deductions and credits
- local city/county sales tax lookups

Keep the same input/output models in `backend/app/models.py` and the Angular widget will continue to work.

## Azure DevOps Deployment Notes

`azure-pipelines.yml` is a starter pipeline that:

- installs Python dependencies
- runs backend tests if present
- installs frontend dependencies
- builds the Angular app
- publishes build artifacts

For production deployment, add your own Azure App Service, Static Web App, Key Vault, and service connection tasks.

## Sources Used For Demo Federal Constants

- IRS federal tax rates and brackets: https://www.irs.gov/filing/federal-income-tax-rates-and-brackets
- IRS 2025 standard deduction overview: https://www.irs.gov/newsroom/new-and-enhanced-deductions-for-individuals

