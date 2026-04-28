# Developer Guide

This guide explains how the prototype is built, how to run it, and where to make changes.

## Tech Stack

Frontend:

```text
Angular
TypeScript
CSS
```

Backend:

```text
Python
FastAPI
Pydantic
Azure OpenAI SDK
MongoDB driver
Azure Blob Storage SDK
```

DevOps:

```text
Azure DevOps Git
Azure Pipelines
```

## Local Run

### Start Backend

From the project root:

```powershell
.\start-backend.ps1
```

Or manually:

```powershell
cd backend
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Start Frontend

From the project root:

```powershell
.\start-frontend.ps1
```

Or manually:

```powershell
cd frontend
npm install
npm start
```

Open:

```text
http://localhost:4200
```

## Backend Request Flow

```text
POST /api/estimate
  |
  v
parse_natural_language()
  |  tries Azure OpenAI JSON extraction first
  |  falls back to regex if Azure OpenAI is not configured
  |
  v
estimate_tax()
  |
  v
generate_summary()
  |
  v
save_estimate()
  |
  v
EstimateResponse
```

## API Contract

Endpoint:

```text
POST http://127.0.0.1:8000/api/estimate
```

Request:

```json
{
  "query": "Estimate federal tax for single filer earning $120,000 with $5,000 credits.",
  "save": true
}
```

Response:

```json
{
  "parsed_input": {},
  "estimate": {},
  "summary": "Plain English explanation",
  "disclaimer": "Demo estimate only...",
  "saved": false,
  "storage_status": "not_configured"
}
```

## Key Backend Files

### `backend/app/main.py`

FastAPI application. Defines:

```text
GET /health
POST /api/estimate
```

Change this file when adding new API endpoints.

### `backend/app/models.py`

Pydantic request and response models. Keep this stable because frontend TypeScript models mirror it.

### `backend/app/nl_parser.py`

Natural-language parser.

When Azure OpenAI variables are configured, this file asks GPT-4.5 to return structured JSON.

When Azure OpenAI is not configured or the model response fails validation, it automatically falls back to the local regex parser.

It extracts:

```text
tax type
filing status
income
deductions
credits
purchase amount
state
use tax flag
```

Improve this file if example prompts are not parsed correctly.

### `backend/app/tax_engine.py`

The isolated tax calculation engine.

Main function:

```python
def estimate_tax(parsed: ParsedTaxInput, rates_path: Path | None = None) -> TaxEstimate:
```

This is the best place for tax specialists to work.

### `backend/app/summary_service.py`

Uses Azure OpenAI if environment variables are configured.

If not configured, returns a deterministic fallback summary.

### `backend/app/storage_service.py`

Saves estimate payloads to MongoDB and/or Azure Blob Storage when configured.

## Key Frontend Files

### `frontend/src/app/tax-widget.component.ts`

Main widget UI and interaction logic.

Change this for:

```text
screen layout
example prompts
button behavior
result display
error messages
```

### `frontend/src/app/tax-api.service.ts`

HTTP client wrapper.

Change the API URL here if backend port changes.

### `frontend/src/app/tax.models.ts`

TypeScript response/request types.

Keep aligned with `backend/app/models.py`.

### `frontend/src/styles.css`

Global styles for the widget.

## Environment Variables

Create:

```text
backend/.env
```

From:

```text
backend/.env.example
```

Azure OpenAI:

```text
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4.5
AZURE_OPENAI_API_VERSION=2024-10-21
```

MongoDB:

```text
MONGODB_URI=
MONGODB_DATABASE=tax_estimator
MONGODB_COLLECTION=estimates
```

Azure Storage:

```text
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=tax-estimates
```

Restart backend after changing `.env`.

## Build Commands

Backend syntax check:

```powershell
cd backend
py -m compileall app
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Adding More States

Update:

```text
backend/data/sales_tax_rates.json
```

Example:

```json
"NJ": {
  "name": "New Jersey",
  "state_rate": 0.06625
}
```

Then update:

```text
backend/app/nl_parser.py
```

Add:

```python
"new jersey": "NJ",
```

## Improving The Parser

For a codeathon, keep the parser contract simple. The model should extract fields, not calculate tax.

Good examples to support:

```text
income is $120,000
earning $120,000
$5,000 credits
credits $5,000
itemized deductions are $40k
sales tax for $2,500 in California
```

Avoid building a full NLP engine unless all core demo pieces already work.

## GenAI Parsing Contract

The model is prompted to return only JSON with:

```json
{
  "tax_type": "federal",
  "filing_status": "single",
  "gross_income": 120000,
  "deductions": null,
  "credits": 5000,
  "purchase_amount": null,
  "state": null,
  "is_use_tax": false,
  "confidence": 0.9,
  "missing_fields": []
}
```

Allowed `tax_type` values:

```text
federal
sales_use
```

Allowed `filing_status` values:

```text
single
married_filing_jointly
married_filing_separately
head_of_household
```

The backend validates the JSON with Pydantic before calculating tax.

## Deployment Notes

The included `azure-pipelines.yml` builds backend and frontend artifacts.

For a full Azure deployment, add:

```text
Azure Static Web Apps or Storage Static Website for frontend
Azure App Service for backend
Azure Key Vault for secrets
Application Settings for environment variables
```

## Coding Rules For The Team

1. Keep API models stable.
2. Keep tax logic in `tax_engine.py`.
3. Keep GenAI explanation separate from calculation.
4. Commit small working changes.
5. Do not add complex features until the demo path is reliable.
