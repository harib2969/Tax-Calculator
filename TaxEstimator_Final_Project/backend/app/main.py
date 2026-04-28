from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import EstimateRequest, EstimateResponse
from .nl_parser import parse_natural_language
from .storage_service import save_estimate
from .summary_service import generate_summary
from .tax_engine import estimate_tax


load_dotenv()

app = FastAPI(title="Tax Estimator GenAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCLAIMER = (
    "Demo estimate only. Not tax, legal, or accounting advice. Validate rates, deductions, "
    "credits, nexus, exemptions, and local jurisdictions before real use."
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/estimate", response_model=EstimateResponse)
def create_estimate(request: EstimateRequest) -> EstimateResponse:
    try:
        parsed = parse_natural_language(request.query)
        if parsed.missing_fields:
            raise ValueError("Missing required fields: " + ", ".join(parsed.missing_fields))

        estimate = estimate_tax(parsed)
        summary = generate_summary(request.query, parsed, estimate)
        response = EstimateResponse(
            parsed_input=parsed,
            estimate=estimate,
            summary=summary,
            disclaimer=DISCLAIMER,
            saved=False,
            storage_status="skipped",
        )

        if request.save:
            try:
                response.storage_status = save_estimate(response)
                response.saved = response.storage_status == "saved"
            except Exception:
                response.storage_status = "failed"

        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

