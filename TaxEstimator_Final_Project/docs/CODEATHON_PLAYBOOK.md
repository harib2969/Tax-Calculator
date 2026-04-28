# 16-Hour Codeathon Playbook

Use this as your team operating plan for the GenAI-backed Angular Tax Estimator Widget.

## Goal

Build and present a working prototype that lets a user ask a U.S. tax estimate question in natural language and receive:

1. A structured interpretation of the question.
2. A federal income tax or sales/use tax estimate.
3. A GenAI-style summary.
4. Optional saved history through MongoDB and Azure Storage.

Keep the scope intentionally focused. A polished, reliable demo usually beats a large unfinished idea.

## Winning Demo Story

Use this one-minute story:

```text
Tax questions usually start in plain English, but tax engines require structured inputs. Our widget bridges that gap.

The user asks a federal income tax or sales/use tax question naturally. The Angular widget sends it to a Python API, which uses Azure OpenAI GPT-4.5 to extract structured JSON, runs an isolated deterministic tax engine, and uses Azure OpenAI to generate an explanation. MongoDB and Azure Storage can persist the estimate for history and audit.

The key design choice is separation: the tax engine is isolated, so a tax specialist can improve the calculation without changing the UI or GenAI workflow.
```

## Recommended Team Split

### Person 1: Frontend

Owns:

```text
frontend/src/app/tax-widget.component.ts
frontend/src/styles.css
```

Tasks:

1. Make the widget look polished.
2. Add example prompt buttons.
3. Make result cards clear.
4. Show saved status and disclaimers.

### Person 2: Backend API

Owns:

```text
backend/app/main.py
backend/app/models.py
backend/app/nl_parser.py
```

Tasks:

1. Improve natural-language field extraction.
2. Add validation messages.
3. Keep API responses stable.

### Person 3: Tax Logic

Owns:

```text
backend/app/tax_engine.py
backend/data/sales_tax_rates.json
```

Tasks:

1. Improve federal estimate calculations.
2. Add more states.
3. Add more clear details in the response.
4. Add a small set of test cases if time permits.

### Person 4: Azure + DevOps

Owns:

```text
backend/app/summary_service.py
backend/app/storage_service.py
azure-pipelines.yml
```

Tasks:

1. Configure Azure OpenAI.
2. Configure MongoDB.
3. Configure Azure Storage.
4. Push to Azure DevOps.
5. Run build pipeline.

## 16-Hour Timeline

### Hour 0-1: Setup

1. Everyone installs Node.js, Python, Git.
2. Clone repo from Azure DevOps.
3. Run backend locally.
4. Run frontend locally.
5. Confirm one federal example and one sales tax example work.

Exit criteria:

```text
Frontend opens at http://localhost:4200
Backend health check returns ok
At least one estimate works
```

### Hour 1-3: Stabilize Demo

1. Confirm all example prompts work.
2. Add any missing state names needed for demo.
3. Make error messages friendly.
4. Verify the app works without Azure credentials.

Exit criteria:

```text
The demo works offline with fallback summary.
```

### Hour 3-6: Azure OpenAI Integration

1. Add Azure OpenAI endpoint/key/deployment to `backend/.env`.
2. Restart backend.
3. Compare fallback summary with GPT summary.
4. Tune prompt in `summary_service.py`.

Exit criteria:

```text
Summary is concise, business-friendly, and includes a disclaimer.
```

### Hour 6-8: Persistence

1. Configure MongoDB.
2. Configure Azure Storage.
3. Turn `save` on in the UI.
4. Confirm saved estimate appears in MongoDB.
5. Confirm audit JSON appears in Azure Blob Storage.

Exit criteria:

```text
At least one estimate is saved somewhere.
```

### Hour 8-11: UI Polish

1. Improve visual hierarchy.
2. Add better empty/error/loading states.
3. Make mobile layout readable.
4. Make judge-friendly examples obvious.

Exit criteria:

```text
A first-time viewer understands the app in 10 seconds.
```

### Hour 11-13: Tax Logic Improvements

1. Improve demo states.
2. Add line-item explanation for federal brackets.
3. Add limitations note for sales/use tax local rates.
4. Add a few known expected outputs in notes or tests.

Exit criteria:

```text
You can explain exactly what the prototype calculates and what it does not calculate.
```

### Hour 13-15: Azure DevOps + Packaging

1. Commit all code.
2. Push to Azure DevOps.
3. Run pipeline.
4. Create final demo script.
5. Decide who presents which part.

Exit criteria:

```text
Repo is clean, pipeline builds, demo script is ready.
```

### Hour 15-16: Practice

Run the demo three times:

1. Federal income tax example.
2. Sales tax example.
3. One error-handling example.

Practice the pitch and keep it under the time limit.

## Must-Have Features

Build these first:

1. Angular widget accepts natural-language prompt.
2. Python API returns estimate.
3. Separate tax engine file exists.
4. GenAI summary works or fallback summary works.
5. README and guides are clear.

## Nice-To-Have Features

Only add after must-haves are stable:

1. MongoDB estimate history.
2. Azure Blob audit export.
3. Better sales/use tax state coverage.
4. More advanced parser.
5. Deployed frontend/backend.

## Demo Prompts

Federal:

```text
Estimate federal tax for single filer earning $120,000 with $5,000 credits.
```

Federal with itemized deductions:

```text
I am married filing jointly, income is $210k, itemized deductions are $40k, credits $2,000.
```

Sales tax:

```text
Sales tax for a $2,500 laptop shipped to California.
```

Use tax:

```text
Use tax estimate for $900 purchase in New York.
```

## Judge Questions And Answers

### Is this tax advice?

No. It is a planning prototype. Production use would require verified federal, state, local, exemption, nexus, and filing-rule data.

### Why Angular?

Angular is a strong fit for enterprise widgets because it supports structured components, forms, services, and maintainable TypeScript.

### Why Python?

Python keeps tax calculation and GenAI orchestration easy to read and change during the codeathon.

### Where is GenAI used?

GenAI is used twice: first to extract structured JSON from the user's natural-language question, and then to summarize the structured calculation result in plain English. The calculation itself stays deterministic in `tax_engine.py`.

### Why keep calculation separate from GenAI?

This avoids making the model responsible for arithmetic and tax rules. The model explains; the tax engine calculates.

## Final Presentation Checklist

1. Browser is already open at `http://localhost:4200`.
2. Backend is already running.
3. Azure OpenAI credentials are loaded if available.
4. Have fallback summary ready if Azure access fails.
5. Show `tax_engine.py` to prove calculation is separate.
6. Show MongoDB or Azure Blob only if it works reliably.
7. Mention limitations honestly.
