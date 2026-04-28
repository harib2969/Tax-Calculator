# Beginner Step-by-Step Guide

Build a working Angular + Python GenAI tax estimator demo from zero to running locally.

This guide assumes you are new to Angular, Python APIs, Azure OpenAI, MongoDB, and Azure DevOps. Follow the steps in order.

## 1. What You Are Building

You are building a web widget where a user types a natural-language tax question like:

```text
Estimate federal tax for single filer earning $120,000 with $5,000 credits.
```

The app will:

1. Read the natural-language question.
2. Use Azure OpenAI GPT-4.5 to extract values like income, filing status, purchase amount, and state into structured JSON.
3. Run a tax estimate using a separate Python tax calculation file.
4. Generate a plain-English summary.
5. Optionally save the estimate to MongoDB and Azure Storage.
6. Show the result in an Angular widget.

## 2. Project Architecture

```text
User
  |
  v
Angular Widget Frontend
  |
  | HTTP POST /api/estimate
  v
FastAPI Python Backend
  |
  +--> Azure OpenAI JSON parser, with regex fallback
  |
  +--> Separate tax engine
  |
  +--> Azure OpenAI summary service
  |
  +--> Optional MongoDB / Azure Storage save
```

Important files:

```text
frontend/src/app/tax-widget.component.ts
```

This is the main Angular widget UI.

```text
backend/app/main.py
```

This is the backend API entry point.

```text
backend/app/nl_parser.py
```

This extracts values from the user's natural-language query.

```text
backend/app/tax_engine.py
```

This contains the tax calculation logic. This file is intentionally separate so your team can replace or improve it quickly.

```text
backend/app/summary_service.py
```

This calls Azure OpenAI if credentials are configured. If not configured, it returns a local fallback summary so the demo still works.

## 3. Prerequisites

Install these first.

### 3.1 Install Node.js

Download Node.js from:

```text
https://nodejs.org/
```

Recommended version:

```text
Node.js 20 or newer
```

After installing, close and reopen your terminal.

Check installation:

```powershell
node --version
npm --version
```

Expected:

```text
v20.x.x or newer
10.x.x or newer
```

If PowerShell says `node` is not recognized, try this in the same terminal:

```powershell
$env:Path = "C:\Program Files\nodejs;" + $env:Path
node --version
npm --version
```

### 3.2 Install Python

Download Python from:

```text
https://www.python.org/downloads/
```

Recommended version:

```text
Python 3.11 or newer
```

During installation, enable:

```text
Add Python to PATH
```

Check installation:

```powershell
py --version
py -m pip --version
```

### 3.3 Install Git

Download Git from:

```text
https://git-scm.com/downloads
```

Check installation:

```powershell
git --version
```

Git is needed for Azure DevOps code storage.

### 3.4 Optional Azure Services

For the best codeathon demo, ask your organizers or team for:

```text
Azure OpenAI endpoint
Azure OpenAI API key
Azure OpenAI GPT-4.5 deployment name
MongoDB connection string
Azure Storage connection string
Azure DevOps project/repo
```

The app can still run without Azure OpenAI, MongoDB, or Azure Storage.

## 4. Get The Code

If you already have the folder:

```powershell
cd "C:\Users\Narsi\Downloads\Tax Estimator"
```

If you are using Azure DevOps Git later, your flow will be:

```powershell
git clone <your-azure-devops-repo-url>
cd <repo-folder>
```

## 5. Backend Setup

The backend is the Python API.

### 5.1 Open Backend Folder

```powershell
cd "C:\Users\Narsi\Downloads\Tax Estimator\backend"
```

### 5.2 Create Virtual Environment

Try:

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then try again:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should see:

```text
(.venv)
```

at the beginning of your terminal line.

### 5.3 Install Backend Packages

```powershell
pip install -r requirements.txt
```

If `pip` is not found:

```powershell
py -m pip install -r requirements.txt
```

### 5.4 Configure Environment Variables

Create a local `.env` file:

```powershell
Copy-Item .env.example .env
```

Open:

```text
backend/.env
```

For a no-Azure local demo, you can leave everything blank.

For Azure OpenAI, fill:

```text
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4.5
AZURE_OPENAI_API_VERSION=2024-10-21
```

For MongoDB, fill:

```text
MONGODB_URI=your-mongodb-connection-string
MONGODB_DATABASE=tax_estimator
MONGODB_COLLECTION=estimates
```

For Azure Storage, fill:

```text
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_STORAGE_CONTAINER=tax-estimates
```

### 5.5 Run Backend Server

```powershell
uvicorn app.main:app --reload --port 8000
```

If `uvicorn` is not found:

```powershell
py -m uvicorn app.main:app --reload --port 8000
```

Expected output:

```text
Uvicorn running on http://127.0.0.1:8000
```

Keep this terminal open.

### 5.6 Test Backend Health

Open a second PowerShell terminal and run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected result:

```text
status
------
ok
```

### 5.7 Test Backend Estimate API

Run:

```powershell
$body = @{
  query = "Estimate federal tax for single filer earning $120,000 with $5,000 credits."
  save = $false
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/estimate `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Expected:

You should see parsed input, estimated tax, effective rate, and a summary.

## 6. Frontend Setup

The frontend is the Angular widget.

### 6.1 Open Frontend Folder

Open a new PowerShell terminal:

```powershell
cd "C:\Users\Narsi\Downloads\Tax Estimator\frontend"
```

### 6.2 Install Frontend Packages

```powershell
npm install
```

This may take a few minutes.

If PowerShell says `npm.ps1 cannot be loaded`, use:

```powershell
npm.cmd install
```

If PowerShell says `npm` is not recognized:

```powershell
$env:Path = "C:\Program Files\nodejs;" + $env:Path
npm.cmd install
```

### 6.3 Build Frontend

```powershell
npm run build
```

Expected:

```text
Application bundle generation complete.
```

### 6.4 Run Frontend Server

```powershell
npm start
```

Expected:

```text
Local: http://localhost:4200/
```

Open this in your browser:

```text
http://localhost:4200
```

## 7. Full Local Demo Flow

You need two terminals open.

Terminal 1:

```powershell
cd "C:\Users\Narsi\Downloads\Tax Estimator\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal 2:

```powershell
cd "C:\Users\Narsi\Downloads\Tax Estimator\frontend"
npm start
```

Browser:

```text
http://localhost:4200
```

Try these questions:

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

## 8. How To Explain The Demo To Judges

Use this simple script:

```text
This is an Angular tax-estimator widget backed by a Python FastAPI service.
The user can ask a tax question in plain English.
The backend extracts structured tax inputs, calculates an estimate using a separate tax engine, and generates a GenAI-style explanation with Azure OpenAI when configured.
The calculation engine is isolated, so tax logic can be replaced with a more advanced model, a vendor API, or jurisdiction-specific tax tables.
MongoDB and Azure Storage are included as optional persistence layers for estimate history and audit exports.
```

## 9. What To Improve During The Codeathon

Recommended team split:

```text
Person 1: Angular UI and presentation polish
Person 2: Python API and natural-language parser
Person 3: Tax calculation logic
Person 4: Azure OpenAI, MongoDB, Azure Storage, Azure DevOps deployment
```

Best improvements:

1. Add more filing statuses and deduction options.
2. Add state income tax if time permits.
3. Replace demo sales tax rates with real jurisdiction rates.
4. Add MongoDB history screen.
5. Add Azure OpenAI prompt tuning.
6. Add unit tests for `tax_engine.py`.
7. Deploy frontend and backend to Azure.

## 10. How To Modify The Tax Calculation

Open:

```text
backend/app/tax_engine.py
```

The main function is:

```python
def estimate_tax(parsed: ParsedTaxInput, rates_path: Path | None = None) -> TaxEstimate:
```

Do not change the frontend if possible.

Try to keep the same input:

```python
ParsedTaxInput
```

And same output:

```python
TaxEstimate
```

That way, your UI and API contract stay stable while your tax calculation improves.

## 11. How To Add More Sales Tax States

Open:

```text
backend/data/sales_tax_rates.json
```

Add a state:

```json
"NJ": {
  "name": "New Jersey",
  "state_rate": 0.06625
}
```

Then open:

```text
backend/app/nl_parser.py
```

Add the state name to `STATE_NAMES`:

```python
"new jersey": "NJ",
```

Also add `NJ` to the state-code regex if needed.

## 12. Azure OpenAI Setup

In Azure Portal:

1. Create or open an Azure OpenAI resource.
2. Deploy a GPT-4.5 model.
3. Copy the endpoint.
4. Copy the API key.
5. Copy the deployment name.

Put them in:

```text
backend/.env
```

Example:

```text
AZURE_OPENAI_ENDPOINT=https://my-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=abc123
AZURE_OPENAI_DEPLOYMENT=gpt-4.5
AZURE_OPENAI_API_VERSION=2024-10-21
```

Restart the backend after changing `.env`.

## 13. MongoDB Setup

If using MongoDB Atlas:

1. Create a free cluster.
2. Create a database user.
3. Allow your IP address.
4. Copy the connection string.
5. Put it in `backend/.env`.

Example:

```text
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DATABASE=tax_estimator
MONGODB_COLLECTION=estimates
```

Restart the backend.

When `save` is true, estimate records will be inserted into MongoDB.

## 14. Azure Storage Setup

In Azure Portal:

1. Create a Storage Account.
2. Open Access Keys.
3. Copy the connection string.
4. Put it in `backend/.env`.

Example:

```text
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER=tax-estimates
```

Restart the backend.

The backend will create JSON audit blobs for saved estimates.

## 15. Azure DevOps Setup

### 15.1 Create Repo

1. Open Azure DevOps.
2. Create a new project.
3. Create a new repository.
4. Copy the repo URL.

### 15.2 Push Code

From the project root:

```powershell
cd "C:\Users\Narsi\Downloads\Tax Estimator"
git init
git add .
git commit -m "Initial tax estimator demo"
git branch -M main
git remote add origin <your-azure-devops-repo-url>
git push -u origin main
```

### 15.3 Pipeline

The file already exists:

```text
azure-pipelines.yml
```

In Azure DevOps:

1. Go to Pipelines.
2. Create Pipeline.
3. Select Azure Repos Git.
4. Select your repo.
5. Choose Existing Azure Pipelines YAML file.
6. Select `azure-pipelines.yml`.
7. Run pipeline.

## 16. Troubleshooting

### Problem: `node` or `npm` is not recognized

Fix:

```powershell
$env:Path = "C:\Program Files\nodejs;" + $env:Path
node --version
npm --version
```

Then restart PowerShell later.

### Problem: `npm.ps1 cannot be loaded`

Use:

```powershell
npm.cmd install
npm.cmd start
```

### Problem: Angular build says `spawn EPERM`

Try running PowerShell as normal user again after closing VS Code terminals.

Then:

```powershell
npm.cmd run build
```

If an antivirus or corporate security tool blocks it, ask your organizer or admin.

### Problem: Backend port 8000 is already in use

Run backend on another port:

```powershell
uvicorn app.main:app --reload --port 8001
```

Then update:

```text
frontend/src/app/tax-api.service.ts
```

Change:

```typescript
private readonly apiUrl = 'http://localhost:8000/api/estimate';
```

To:

```typescript
private readonly apiUrl = 'http://localhost:8001/api/estimate';
```

### Problem: Frontend port 4200 is already in use

Run:

```powershell
npm start -- --port 4300
```

Open:

```text
http://localhost:4300
```

### Problem: API says missing field

Your question may not include enough detail.

For federal tax, include:

```text
filing status
income
deductions or credits if relevant
```

For sales/use tax, include:

```text
purchase amount
state
```

### Problem: Azure OpenAI summary is not working

The app will still use a fallback summary.

Check:

1. `.env` values are correct.
2. Backend was restarted after `.env` changes.
3. Deployment name exactly matches Azure OpenAI deployment name.
4. API key is valid.

## 17. Final Codeathon Checklist

Before presenting:

1. Backend starts on port 8000.
2. Frontend starts on port 4200.
3. Federal tax example works.
4. Sales tax example works.
5. Summary appears.
6. You can explain that `tax_engine.py` is replaceable.
7. README and this beginner guide are committed.
8. Azure DevOps repo has latest code.
9. Optional services are either configured or clearly explained as optional.

## 18. Important Demo Disclaimer

Use this line during the presentation:

```text
This is a planning and workflow demo, not production tax advice. Real deployment would require verified federal, state, local, exemption, nexus, and filing-rule data.
```
