"""routers/analyze.py — POST /api/analyze"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import logging

from tax_engine import TaxInput, calculate_sales_use_tax

log = logging.getLogger(__name__)
router = APIRouter()


class AnalyzeRequest(BaseModel):
    query: str


@router.post("/analyze")
def analyze(body: AnalyzeRequest, request: Request):
    llm     = request.app.state.llm
    storage = request.app.state.storage

    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # ── Step 1: LLM / rule-based extraction ─────────────────────────────────
    try:
        extracted = llm.extract(body.query)
    except Exception as e:
        log.error(f"LLM extraction error: {e}")
        raise HTTPException(status_code=502, detail=f"Extraction failed: {str(e)}")

    if not extracted.get("sale_amount"):
        return {
            "error": "no_amount",
            "message": "I couldn't find a dollar amount in your query. Try: 'I sold $8,000 of software to a customer in Texas'",
            "extracted": extracted,
        }

    if not extracted.get("state"):
        return {
            "error": "no_state",
            "message": "I couldn't identify a US state. Please mention the state where the sale occurred.",
            "extracted": extracted,
        }

    # ── Step 2: Tax engine ───────────────────────────────────────────────────
    try:
        tax_input = TaxInput(
            sale_amount                 = float(extracted["sale_amount"]),
            state                       = extracted["state"],
            product_type                = extracted.get("product_type", "physical_goods"),
            is_use_tax                  = bool(extracted.get("is_use_tax", False)),
            business_type               = extracted.get("business_type", "b2c"),
            annual_sales_in_state       = float(extracted.get("annual_sales_in_state") or 0),
            annual_transactions_in_state= int(extracted.get("annual_transactions_in_state") or 0),
            has_physical_presence       = bool(extracted.get("has_physical_presence", False)),
        )
        tax_result = calculate_sales_use_tax(tax_input)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error(f"Tax engine error: {e}")
        raise HTTPException(status_code=500, detail="Tax calculation failed.")

    # ── Step 3: Flatten result for response + summary ────────────────────────
    result_dict = {
        "state":           tax_result.state,
        "state_name":      tax_result.state_name,
        "sale_amount":     tax_result.sale_amount,
        "product_type":    tax_result.product_type,
        "tax_type_label":  tax_result.tax_type_label,
        "rate_pct":        tax_result.rate_pct,
        "tax_amount":      tax_result.tax_amount,
        "total_due":       tax_result.total_due,
        "has_nexus":       tax_result.nexus.has_nexus,
        "nexus_reason":    tax_result.nexus.reason,
        "is_exempt":       tax_result.exemption.is_exempt,
        "exemption_reason":tax_result.exemption.reason,
        "notes":           tax_result.notes,
    }

    # ── Step 4: AI summary ───────────────────────────────────────────────────
    try:
        result_dict["summary"] = llm.summarize(result_dict)
    except Exception as e:
        log.warning(f"Summary generation failed: {e}")
        result_dict["summary"] = result_dict["notes"][0] if result_dict["notes"] else ""

    # ── Step 5: Persist ──────────────────────────────────────────────────────
    try:
        storage.save_query(body.query, extracted, result_dict)
    except Exception as e:
        log.warning(f"Storage save failed (non-fatal): {e}")

    result_dict["extracted"] = extracted
    return result_dict
