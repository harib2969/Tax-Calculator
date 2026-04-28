import json
from pathlib import Path

from .models import FilingStatus, ParsedTaxInput, TaxEstimate, TaxType


STANDARD_DEDUCTIONS_2025 = {
    FilingStatus.SINGLE: 15750,
    FilingStatus.MARRIED_FILING_JOINTLY: 31500,
    FilingStatus.MARRIED_FILING_SEPARATELY: 15750,
    FilingStatus.HEAD_OF_HOUSEHOLD: 23625,
}

BRACKETS_2025 = {
    FilingStatus.SINGLE: [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (626350, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.MARRIED_FILING_JOINTLY: [
        (23850, 0.10),
        (96950, 0.12),
        (206700, 0.22),
        (394600, 0.24),
        (501050, 0.32),
        (751600, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.MARRIED_FILING_SEPARATELY: [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (375800, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.HEAD_OF_HOUSEHOLD: [
        (17000, 0.10),
        (64850, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250500, 0.32),
        (626350, 0.35),
        (float("inf"), 0.37),
    ],
}


def estimate_tax(parsed: ParsedTaxInput, rates_path: Path | None = None) -> TaxEstimate:
    if parsed.tax_type == TaxType.FEDERAL:
        return estimate_federal_income_tax(parsed)
    return estimate_sales_use_tax(parsed, rates_path)


def estimate_federal_income_tax(parsed: ParsedTaxInput) -> TaxEstimate:
    if parsed.gross_income is None:
        raise ValueError("gross_income is required for federal tax estimates")

    status = parsed.filing_status or FilingStatus.SINGLE
    deduction = parsed.deductions if parsed.deductions is not None else STANDARD_DEDUCTIONS_2025[status]
    taxable_income = max(parsed.gross_income - deduction, 0)
    raw_tax, marginal_rate, layers = _progressive_tax(taxable_income, BRACKETS_2025[status])
    estimated_tax = max(raw_tax - parsed.credits, 0)

    return TaxEstimate(
        tax_type=TaxType.FEDERAL,
        taxable_amount=round(taxable_income, 2),
        estimated_tax=round(estimated_tax, 2),
        effective_rate=round(estimated_tax / parsed.gross_income, 4) if parsed.gross_income else 0,
        marginal_rate=marginal_rate,
        details={
            "tax_year": 2025,
            "filing_status": status,
            "gross_income": parsed.gross_income,
            "deduction_used": deduction,
            "credits_used": parsed.credits,
            "tax_before_credits": round(raw_tax, 2),
            "bracket_layers": layers,
        },
    )


def estimate_sales_use_tax(parsed: ParsedTaxInput, rates_path: Path | None = None) -> TaxEstimate:
    if parsed.purchase_amount is None:
        raise ValueError("purchase_amount is required for sales/use tax estimates")
    if not parsed.state:
        raise ValueError("state is required for sales/use tax estimates")

    rates_path = rates_path or Path(__file__).resolve().parents[1] / "data" / "sales_tax_rates.json"
    rates = json.loads(rates_path.read_text(encoding="utf-8"))
    state_rate = rates.get(parsed.state.upper(), {}).get("state_rate")
    if state_rate is None:
        raise ValueError(f"No demo sales/use tax rate configured for state {parsed.state}")

    estimated_tax = parsed.purchase_amount * state_rate
    return TaxEstimate(
        tax_type=TaxType.SALES_USE,
        taxable_amount=round(parsed.purchase_amount, 2),
        estimated_tax=round(estimated_tax, 2),
        effective_rate=round(state_rate, 4),
        marginal_rate=None,
        details={
            "state": parsed.state.upper(),
            "state_rate": state_rate,
            "is_use_tax": parsed.is_use_tax,
            "rate_note": "Demo state-level rate only; local city/county/special district rates are not included.",
        },
    )


def _progressive_tax(taxable_income: float, brackets: list[tuple[float, float]]) -> tuple[float, float, list[dict]]:
    previous_limit = 0.0
    total_tax = 0.0
    marginal_rate = 0.0
    layers = []

    for limit, rate in brackets:
        if taxable_income <= previous_limit:
            break
        taxable_in_layer = min(taxable_income, limit) - previous_limit
        layer_tax = taxable_in_layer * rate
        total_tax += layer_tax
        marginal_rate = rate
        layers.append(
            {
                "from": previous_limit,
                "to": "and_up" if limit == float("inf") else limit,
                "rate": rate,
                "taxed_amount": round(taxable_in_layer, 2),
                "tax": round(layer_tax, 2),
            }
        )
        previous_limit = limit

    return total_tax, marginal_rate, layers

