# Tax Lens — Run Steps

You need three things running:

1. **MongoDB** (or skip — backend falls back to in-memory)
2. **FastAPI backend** on `http://localhost:8000`
3. **Angular frontend** on `http://localhost:4200`

---

## 1. Place the Excel file

```
backend/
  data/
    sample-org-tax 1.xlsx     ← put it here (keep the space in the name)
```

Or change `EXCEL_PATH` in `backend/.env`.

---

## 2. Backend — FastAPI

```powershell
# from project root
cd backend

# (one-time) create + activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install deps
pip install -r requirements.txt

# create .env from template and FILL IN your Azure + Mongo details
copy .env.example .env
notepad .env       # set AZURE_OPENAI_ENDPOINT, KEY, DEPLOYMENT, MONGO_URI

# run the server (auto-reload during dev)
uvicorn main:app --reload --port 8000
```

You should see something like:
```
[OK]  Loaded 26 companies from data/sample-org-tax 1.xlsx
[DB]  connected to MongoDB: tax_lens
[AI]  Azure OpenAI configured (deployment=YOUR-DEPLOY, api_version=2024-08-01-preview)
```

Verify: open `http://localhost:8000/companies` in a browser → JSON list.

---

## 3. Frontend — Angular

```powershell
# from project root, in a NEW terminal
cd frontend

# install deps (Node 18+ required)
npm install

# run dev server (proxies /api → :8000)
npm start
```

Open `http://localhost:4200`.

You should see:
- The company portfolio grid populated
- Click a row → full 7-step tax breakdown appears below
- Type in the chat → AI responds with tool-call chips visible

---

## 4. (Optional) MongoDB

If you have it running locally:
```
MONGO_URI=mongodb://localhost:27017
```

If using Atlas, paste the full SRV connection string. If you don't set
`MONGO_URI`, the backend transparently falls back to an in-memory store —
sessions just disappear when you restart the server.

---

## Smoke tests

After both servers are up, try in the chat:
1. *"List all C-Corps in California"* → should call `filter_companies`
2. *"Walk me through how you calculated Pacific Manufacturing Co's tax"* → step-by-step
3. *"What if Pine Grove moved to Texas and added 100k more deductions?"* → multi-override what-if
4. *"Top 3 companies by effective rate"* → `top_n_analysis`
5. *"Compare Pacific Manufacturing and Atlas Construction"* → `compare_companies`
6. *"Which companies could save the most by restructuring?"* → `tax_savings_opportunities`

Each reply shows the tool(s) the agent called as small green chips.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend says `[AI] NOT configured` | Fill in `.env` and restart |
| Chat returns "Azure OpenAI is not configured" | Same — backend can't reach Azure |
| Frontend grid empty | Check backend started OK; check Excel file path; verify `/api/companies` returns JSON |
| CORS error | Make sure you started Angular with `npm start` (proxy is wired in) |
| `AZURE_OPENAI_DEPLOYMENT` errors from OpenAI | Deployment name must match exactly what's in Azure portal |
| Port 8000 already in use | `uvicorn main:app --reload --port 8001` and update `proxy.conf.json` |
