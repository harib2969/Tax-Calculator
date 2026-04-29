# Tax Lens — Architecture & File Reference

A natural-language tax advisory widget combining a deterministic rule-based tax
engine (FastAPI/Python) with an agentic conversational layer (Azure OpenAI
function calling) and a responsive Angular + PrimeNG UI.

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Angular 17 + TS │      │  FastAPI / Py    │      │  Azure OpenAI    │
│ PrimeNG (grid + │ ───► │  Tax Engine      │ ───► │ Function calling │
│ chat panel)     │      │  Excel parser    │      │ (13 tools)       │
└─────────────────┘      └──────────────────┘      └──────────────────┘
                              │
                              ├─► In-memory store (every company pre-computed)
                              └─► MongoDB (chat session history)
```

**Key principle:** the LLM never computes tax math. It picks tools, the engine
returns deterministic JSON, the LLM composes a natural-language answer.

---

## Backend (Python · FastAPI) — `backend/`

### `main.py` — FastAPI entry point
Defines the REST API surface and orchestrates startup.

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Health check + endpoint list |
| `/companies` | GET | List all companies with computed tax summary |
| `/companies/{name}` | GET | Raw company record |
| `/companies/{name}/tax` | GET | Full 7-step tax breakdown |
| `/tax/whatif` | POST | Run a what-if scenario with overrides |
| `/tax/compare` | POST | Compare 2+ companies side-by-side |
| `/tax/portfolio` | GET | Cross-portfolio analytics |
| `/tax/savings-opportunities` | GET | Restructuring recommendations |
| `/chat` | POST | Send a chat message; returns AI reply |
| `/sessions` | GET | List active sessions |
| `/sessions/{id}` | GET | Get full message history |
| `/sessions/{id}` | DELETE | Reset a session |

**Startup (lifespan handler):**
1. Load Excel via `tax_engine.load_companies_from_excel`
2. Pre-compute tax breakdown for every company (in-memory)
3. Connect to MongoDB (or fall back to in-memory store)
4. Cache results to MongoDB for inspection
5. Initialize Azure OpenAI client

### `tax_engine.py` — Pure deterministic tax engine

Implements the **7-step Tax Lens calculation** exactly as specified.

**Constants:**
- `STATE_RATES` — every state's C-Corp and pass-through rate
- `BRACKETS_2024` — 2024 individual income brackets
- `PASS_THROUGH_ENTITIES` — `{"S-Corp", "LLC", "Partnership"}`
- `C_CORP_RATE = 0.21`, `QBI_RATE = 0.20`, `NOL_CAP = 0.80`
- `CA_MIN_FRANCHISE_TAX = 800.0`

**Core functions:**

| Function | Purpose |
|---|---|
| `load_companies_from_excel(path)` | Parses the Excel `Summary` sheet and pre-computes tax for every row |
| `calculate_tax(record)` | Runs all 7 steps; returns `{inputs, steps, summary, explanation}` |
| `_bracket_tax(income)` | Internal: progressive 2024 individual brackets |
| `_state_rate(state, entity)` | Internal: state rate lookup |
| `find_company(name)` | Fuzzy/case-insensitive lookup |

**Tool functions (called by `ai_layer.py`):**

| Tool function | Purpose |
|---|---|
| `get_company_tax_breakdown` | Full 7-step breakdown |
| `what_if_calculator` | Recalculate with arbitrary overrides |
| `recalculate_with_overrides` | Multi-override variant |
| `compare_companies` | Side-by-side comparison |
| `portfolio_analysis` | Cross-portfolio insights |
| `filter_companies` | Filter by entity/state/income/tax |
| `explain_tax_rule` | Static knowledge base of rules |
| `nol_impact_analysis` | Tax saved by NOL |
| `credit_impact_analysis` | Tax saved by credits |
| `state_comparison` | Recalculate across all 10 states |
| `entity_type_comparison` | Recalculate as each entity type |
| `top_n_analysis` | Top N companies by any metric |
| `tax_savings_opportunities` | Restructuring opportunities |

### `ai_layer.py` — Azure OpenAI integration

| Component | Purpose |
|---|---|
| `init_azure_openai()` | Configures client from env vars |
| `SYSTEM_PROMPT` | Defines persona, tone, tool-use discipline |
| `TOOLS` | 13 OpenAI function-calling schemas |
| `_dispatch(name, args)` | Maps tool name → `tax_engine` function |
| `chat_turn(history, user_message)` | Full agentic loop with up to 5 tool iterations |

**Loop logic:** send messages + tool schemas → if model requests tool calls,
execute them and append results → loop until model returns final text answer.

### `db.py` — MongoDB session store

| Function | Purpose |
|---|---|
| `init_db(uri, db_name)` | Connect to Mongo; falls back to in-memory dict |
| `get_session(id)` | Load (or create) a session document |
| `append_messages(id, msgs)` | Push messages to history (with `$push`) |
| `reset_session(id)` | Delete session |
| `list_sessions()` | List recent sessions |
| `cache_tax_results(results)` | Store pre-computed results for inspection |

Collections: `sessions`, `tax_cache`.

### `models.py` — Pydantic request/response models
`Company`, `TaxSteps`, `TaxSummary`, `TaxResult`, `WhatIfRequest`,
`CompareRequest`, `ChatRequest`, `ChatResponse`, `ChatMessage`.

### `requirements.txt` — Pinned dependencies
fastapi, uvicorn, pydantic, pandas, openpyxl, openai, pymongo, python-dotenv.

### `.env.example` — Configuration template
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT`,
  `AZURE_OPENAI_API_VERSION`
- `MONGO_URI`, `MONGO_DB`
- `EXCEL_PATH`

---

## Frontend (Angular 17 · Standalone · PrimeNG) — `frontend/`

### `src/app/tax.types.ts`
TypeScript interfaces mirroring backend models: `Company`, `CompanySummaryRow`,
`TaxSteps`, `TaxSummary`, `TaxBreakdown`, `ChatMessage`, `ChatResponse`.

### `src/app/api.service.ts`
Single HTTP service. Methods: `listCompanies`, `getCompany`, `getCompanyTax`,
`whatIf`, `compare`, `portfolio`, `chat`, `resetSession`. All requests go
through the `/api` proxy to FastAPI on `:8000`.

### `src/app/session.service.ts`
Reactive state for the chat using Angular signals:
- `sessionId` — stable per browser tab (sessionStorage), so MongoDB returns
  the same persistent history
- `messages` — local mirror of conversation
- `selectedCompany` — last clicked company in the grid
- `isThinking` — drives the "Thinking…" indicator

### `src/app/tax-widget.component.ts` — **Main UI**
A single standalone component containing:

- **Header** — branding + companies-loaded badge
- **Left pane** — PrimeNG `<p-table>` (sortable, filterable, paginated) with
  entity-type tag badges; clicking a row calls the API and renders the full
  step-by-step breakdown card
- **Right pane** — chat panel:
  - Empty state with 6 example prompts (click to send)
  - Message bubbles for user/assistant
  - Tool-call chips showing which agent tools fired
  - Spinner when waiting on AI
  - Reset button

All HTML and CSS are inline for minimum file count. Uses PrimeNG: Table,
Button, InputText, Card, Tag, Dialog, ProgressSpinner, Tooltip.

### `src/app/app.component.ts` — Shell
Renders `<tax-widget />`.

### `src/app/app.config.ts` — Bootstrap providers
`provideHttpClient()` and `provideAnimations()`.

### `src/main.ts` — Bootstrap entry
`bootstrapApplication(AppComponent, appConfig)`.

### `src/styles.css` — Global styles
Imports PrimeNG theme `lara-light-indigo` + `primeicons` + `primeflex`.

### `src/index.html` — HTML entry
Minimal — just `<app-root></app-root>`.

### `proxy.conf.json` — Dev API proxy
Routes `/api/*` → `http://localhost:8000`. Configured in `angular.json`.

### `package.json`, `angular.json`, `tsconfig.json`, `tsconfig.app.json`
Standard Angular standalone scaffolding pinned to Angular 17 + PrimeNG 17.

---

## Data flow — a single chat turn

1. User types: *"What if Pacific Manufacturing moved to Texas?"*
2. Angular calls `POST /api/chat` with `{session_id, message}`
3. FastAPI loads prior messages from MongoDB
4. `ai_layer.chat_turn` sends them + 13 tool schemas to Azure OpenAI
5. Model returns a `tool_call` → `what_if_calculator(company="Pacific...", overrides={"StateCode":"TX"})`
6. Dispatcher runs `tax_engine.what_if_calculator` (deterministic math)
7. Result JSON appended to messages; model is called again
8. Model now returns a natural-language explanation citing the numbers
9. New messages persisted to MongoDB; reply returned to Angular
10. Tool-call chips show `["what_if_calculator"]` so the user sees agentic behavior

---

## File count summary

| Category | Files |
|---|---|
| Backend | 6 (`main.py`, `tax_engine.py`, `ai_layer.py`, `db.py`, `models.py`, `requirements.txt`) + `.env.example` |
| Frontend code | 7 (`tax-widget.component.ts`, `app.component.ts`, `app.config.ts`, `main.ts`, `api.service.ts`, `session.service.ts`, `tax.types.ts`) |
| Frontend config | 5 (`package.json`, `angular.json`, `tsconfig.json`, `tsconfig.app.json`, `proxy.conf.json`, `index.html`, `styles.css`) |
| Docs | `ARCHITECTURE.md`, `RUN_STEPS.md`, `presentation.pptx` |

Total: ~21 files, all small (<400 lines each except the main component).
