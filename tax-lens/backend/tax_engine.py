"""
Tax Engine — pure deterministic 7-step calculator + portfolio analytics.

NO AI/ML here. Every number produced by this file is rule-based and explainable.
The AI layer (ai_layer.py) only formats answers; it never computes.
"""
from typing import Any, Optional
import pandas as pd
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS — Tax Lens Tax Calculation Logic Guide
# ──────────────────────────────────────────────────────────────────────────────

PASS_THROUGH_ENTITIES = {"S-Corp", "LLC", "Partnership"}
C_CORP_RATE = 0.21
QBI_RATE = 0.20
NOL_CAP = 0.80
CA_MIN_FRANCHISE_TAX = 800.0

# 2024 individual income tax brackets (used for pass-through entities)
BRACKETS_2024 = [
    (11_600,        0.10),
    (47_150,        0.12),
    (100_525,       0.22),
    (191_950,       0.24),
    (243_725,       0.32),
    (609_350,       0.35),
    (float("inf"),  0.37),
]

# State Tax Rate Reference
STATE_RATES = {
    "CA": {"C-Corp": 0.0884, "pass": 0.0930},
    "NY": {"C-Corp": 0.0650, "pass": 0.1090},
    "TX": {"C-Corp": 0.0000, "pass": 0.0000},
    "FL": {"C-Corp": 0.0550, "pass": 0.0000},
    "IL": {"C-Corp": 0.0950, "pass": 0.0495},
    "WA": {"C-Corp": 0.0000, "pass": 0.0000},
    "PA": {"C-Corp": 0.0899, "pass": 0.0307},
    "OH": {"C-Corp": 0.0000, "pass": 0.0000},
    "MA": {"C-Corp": 0.0800, "pass": 0.0500},
    "NJ": {"C-Corp": 0.0900, "pass": 0.1075},
}


# ──────────────────────────────────────────────────────────────────────────────
# IN-MEMORY STORE (populated on startup by load_companies_from_excel)
# ──────────────────────────────────────────────────────────────────────────────
COMPANIES: dict[str, dict[str, Any]] = {}     # name -> raw record
TAX_RESULTS: dict[str, dict[str, Any]] = {}   # name -> calculated breakdown


# ──────────────────────────────────────────────────────────────────────────────
# EXCEL LOADER
# ──────────────────────────────────────────────────────────────────────────────
def load_companies_from_excel(xlsx_path: str) -> int:
    """Read Summary sheet, store raw records, pre-compute tax for all companies.

    Returns count of companies loaded.
    """
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {xlsx_path}")

    # Try the 'Summary' sheet first; fall back to first sheet
    try:
        df = pd.read_excel(path, sheet_name="Summary")
    except Exception:
        df = pd.read_excel(path, sheet_name=0)

    df = df.fillna(0)
    COMPANIES.clear()
    TAX_RESULTS.clear()

    for _, row in df.iterrows():
        record = {
            "CompanyName":      str(row.get("CompanyName", "")).strip(),
            "GrossIncome":      float(row.get("GrossIncome", 0) or 0),
            "Deductions":       float(row.get("Deductions", 0) or 0),
            "EntityType":       str(row.get("EntityType", "")).strip(),
            "StateCode":        str(row.get("StateCode", "")).strip().upper(),
            "TaxYear":          int(row.get("TaxYear", 2024) or 2024),
            "NOLCarryforward":  float(row.get("NOLCarryforward", 0) or 0),
            "EstimatedPayments": float(row.get("EstimatedPayments", 0) or 0),
            "Credits":          float(row.get("Credits", 0) or 0),
        }
        if not record["CompanyName"]:
            continue
        COMPANIES[record["CompanyName"]] = record
        TAX_RESULTS[record["CompanyName"]] = calculate_tax(record)

    return len(COMPANIES)


# ──────────────────────────────────────────────────────────────────────────────
# CORE 7-STEP CALCULATOR
# ──────────────────────────────────────────────────────────────────────────────
def _bracket_tax(income: float) -> float:
    """Apply 2024 individual brackets progressively."""
    if income <= 0:
        return 0.0
    tax = 0.0
    prev = 0.0
    for limit, rate in BRACKETS_2024:
        if income <= limit:
            tax += (income - prev) * rate
            return tax
        tax += (limit - prev) * rate
        prev = limit
    return tax


def _state_rate(state: str, entity: str) -> float:
    rates = STATE_RATES.get(state.upper())
    if not rates:
        return 0.0
    key = "C-Corp" if entity == "C-Corp" else "pass"
    return rates.get(key, 0.0)


def calculate_tax(record: dict[str, Any]) -> dict[str, Any]:
    """Full 7-step calculation for a single company record. Returns full breakdown."""
    name = record.get("CompanyName", "Unknown")
    gross = float(record.get("GrossIncome", 0) or 0)
    deductions = float(record.get("Deductions", 0) or 0)
    entity = record.get("EntityType", "")
    state = (record.get("StateCode", "") or "").upper()
    nol = float(record.get("NOLCarryforward", 0) or 0)
    credits = float(record.get("Credits", 0) or 0)
    payments = float(record.get("EstimatedPayments", 0) or 0)

    explanation: list[str] = []

    # Step 1 — Federal Taxable Income
    fed_taxable = max(0.0, gross - deductions)
    explanation.append(
        f"Step 1: Federal Taxable Income = max(0, {gross:,.0f} - {deductions:,.0f}) = {fed_taxable:,.0f}"
    )

    # Step 2 — QBI Deduction
    if entity in PASS_THROUGH_ENTITIES:
        qbi = QBI_RATE * fed_taxable
        explanation.append(
            f"Step 2: {entity} is pass-through -> QBI = 20% * {fed_taxable:,.0f} = {qbi:,.0f}"
        )
    else:
        qbi = 0.0
        explanation.append(f"Step 2: {entity} -> no QBI deduction (C-Corps do not qualify)")
    adjusted = max(0.0, fed_taxable - qbi)
    explanation.append(f"        Adjusted Taxable = {fed_taxable:,.0f} - {qbi:,.0f} = {adjusted:,.0f}")

    # Step 3 — NOL Carryforward (capped at 80%)
    nol_used = min(nol, NOL_CAP * adjusted)
    final_taxable = max(0.0, adjusted - nol_used)
    explanation.append(
        f"Step 3: NOL Used = min({nol:,.0f}, 80% * {adjusted:,.0f}) = {nol_used:,.0f}"
    )
    explanation.append(f"        Final Taxable = {adjusted:,.0f} - {nol_used:,.0f} = {final_taxable:,.0f}")

    # Step 4 — Federal Tax Computation
    if entity == "C-Corp":
        fed_tax_pre = final_taxable * C_CORP_RATE
        explanation.append(
            f"Step 4: C-Corp flat 21% -> Federal Tax (pre-credits) = {final_taxable:,.0f} * 21% = {fed_tax_pre:,.0f}"
        )
    else:
        fed_tax_pre = _bracket_tax(final_taxable)
        explanation.append(
            f"Step 4: Pass-through -> 2024 brackets on {final_taxable:,.0f} = {fed_tax_pre:,.0f}"
        )

    # Step 5 — Apply Credits
    fed_tax = max(0.0, fed_tax_pre - credits)
    explanation.append(
        f"Step 5: Federal Tax = max(0, {fed_tax_pre:,.0f} - {credits:,.0f}) = {fed_tax:,.0f}"
    )

    # Step 6 — State Tax (uses pre-QBI base)
    state_taxable = max(0.0, gross - deductions)
    rate = _state_rate(state, entity)
    state_tax_pre = state_taxable * rate
    if state == "CA":
        state_tax = max(CA_MIN_FRANCHISE_TAX, state_tax_pre)
        explanation.append(
            f"Step 6: CA - max($800 min franchise, {state_taxable:,.0f} * {rate:.4f}) = {state_tax:,.0f}"
        )
    else:
        state_tax = state_tax_pre
        explanation.append(
            f"Step 6: {state} - State Tax = {state_taxable:,.0f} * {rate:.4f} = {state_tax:,.0f}"
        )

    # Step 7 — Total + Effective Rate
    total = fed_tax + state_tax
    eff_rate = (total / gross * 100) if gross > 0 else 0.0
    balance_due = total - payments
    explanation.append(
        f"Step 7: Total Tax = {fed_tax:,.0f} + {state_tax:,.0f} = {total:,.0f}; "
        f"Effective Rate = {eff_rate:.2f}%"
    )

    return {
        "company": name,
        "inputs": record,
        "steps": {
            "step1_federal_taxable_income": round(fed_taxable, 2),
            "step2_qbi_deduction": round(qbi, 2),
            "step2_adjusted_taxable": round(adjusted, 2),
            "step3_nol_used": round(nol_used, 2),
            "step3_final_taxable": round(final_taxable, 2),
            "step4_federal_tax_pre_credits": round(fed_tax_pre, 2),
            "step5_federal_tax": round(fed_tax, 2),
            "step6_state_taxable": round(state_taxable, 2),
            "step6_state_rate": rate,
            "step6_state_tax": round(state_tax, 2),
            "step7_total_tax": round(total, 2),
            "step7_effective_rate": round(eff_rate, 4),
        },
        "summary": {
            "federal_tax": round(fed_tax, 2),
            "state_tax": round(state_tax, 2),
            "total_tax": round(total, 2),
            "effective_rate": round(eff_rate, 4),
            "estimated_payments": round(payments, 2),
            "balance_due": round(balance_due, 2),
        },
        "explanation": explanation,
    }


# ──────────────────────────────────────────────────────────────────────────────
# LOOKUPS / TOOL FUNCTIONS (called by ai_layer.py via Azure function calling)
# ──────────────────────────────────────────────────────────────────────────────
def find_company(name: str) -> Optional[dict[str, Any]]:
    """Case-insensitive fuzzy company lookup."""
    if not name:
        return None
    name_l = name.lower().strip()
    if name in COMPANIES:
        return COMPANIES[name]
    for key, rec in COMPANIES.items():
        if key.lower() == name_l:
            return rec
    for key, rec in COMPANIES.items():
        if name_l in key.lower() or key.lower() in name_l:
            return rec
    return None


def get_company_tax_breakdown(company_name: str) -> dict[str, Any]:
    rec = find_company(company_name)
    if not rec:
        return {"error": f"Company not found: {company_name}",
                "available_companies": list(COMPANIES.keys())[:10]}
    return TAX_RESULTS.get(rec["CompanyName"]) or calculate_tax(rec)


def what_if_calculator(company_name: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """Recalculate with arbitrary overrides. Returns original + modified side-by-side."""
    rec = find_company(company_name)
    if not rec:
        return {"error": f"Company not found: {company_name}"}
    original = TAX_RESULTS.get(rec["CompanyName"]) or calculate_tax(rec)
    modified_record = {**rec, **(overrides or {})}
    if "StateCode" in modified_record:
        modified_record["StateCode"] = str(modified_record["StateCode"]).upper()
    modified = calculate_tax(modified_record)
    delta_total = modified["summary"]["total_tax"] - original["summary"]["total_tax"]
    delta_eff = modified["summary"]["effective_rate"] - original["summary"]["effective_rate"]
    return {
        "company": rec["CompanyName"],
        "overrides_applied": overrides,
        "original": original["summary"],
        "modified": modified["summary"],
        "delta": {
            "total_tax_change": round(delta_total, 2),
            "effective_rate_change_pct_points": round(delta_eff, 4),
            "savings": round(-delta_total, 2),
        },
        "modified_breakdown": modified,
    }


def recalculate_with_overrides(company_name: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """Alias for multi-override what-if scenarios."""
    return what_if_calculator(company_name, overrides)


def compare_companies(company_names: list[str]) -> dict[str, Any]:
    rows = []
    not_found = []
    for n in company_names:
        rec = find_company(n)
        if not rec:
            not_found.append(n)
            continue
        r = TAX_RESULTS.get(rec["CompanyName"]) or calculate_tax(rec)
        rows.append({
            "company": rec["CompanyName"],
            "entity": rec["EntityType"],
            "state": rec["StateCode"],
            "gross_income": rec["GrossIncome"],
            "federal_tax": r["summary"]["federal_tax"],
            "state_tax": r["summary"]["state_tax"],
            "total_tax": r["summary"]["total_tax"],
            "effective_rate": r["summary"]["effective_rate"],
        })
    return {"comparison": rows, "not_found": not_found}


def portfolio_analysis() -> dict[str, Any]:
    if not TAX_RESULTS:
        return {"error": "No companies loaded"}
    rows = [{
        "company": name,
        "entity": COMPANIES[name]["EntityType"],
        "state": COMPANIES[name]["StateCode"],
        "gross_income": COMPANIES[name]["GrossIncome"],
        "total_tax": r["summary"]["total_tax"],
        "effective_rate": r["summary"]["effective_rate"],
    } for name, r in TAX_RESULTS.items()]
    rows_sorted_total = sorted(rows, key=lambda x: x["total_tax"], reverse=True)
    rows_sorted_eff = sorted(rows, key=lambda x: x["effective_rate"], reverse=True)
    total_tax_burden = sum(r["total_tax"] for r in rows)
    total_gross = sum(r["gross_income"] for r in rows)
    return {
        "total_companies": len(rows),
        "total_gross_income": round(total_gross, 2),
        "total_tax_burden": round(total_tax_burden, 2),
        "portfolio_effective_rate": round((total_tax_burden / total_gross * 100) if total_gross else 0, 4),
        "highest_tax": rows_sorted_total[:3],
        "lowest_tax": rows_sorted_total[-3:],
        "highest_effective_rate": rows_sorted_eff[:3],
        "lowest_effective_rate": rows_sorted_eff[-3:],
    }


def filter_companies(filters: dict[str, Any]) -> dict[str, Any]:
    """Filter by entity_type, state, min_gross, max_gross, min_total_tax, etc."""
    results = []
    for name, rec in COMPANIES.items():
        r = TAX_RESULTS.get(name)
        if not r:
            continue
        if "entity_type" in filters and rec["EntityType"] != filters["entity_type"]:
            continue
        if "state" in filters and rec["StateCode"] != str(filters["state"]).upper():
            continue
        if "min_gross" in filters and rec["GrossIncome"] < filters["min_gross"]:
            continue
        if "max_gross" in filters and rec["GrossIncome"] > filters["max_gross"]:
            continue
        if "min_total_tax" in filters and r["summary"]["total_tax"] < filters["min_total_tax"]:
            continue
        if "max_total_tax" in filters and r["summary"]["total_tax"] > filters["max_total_tax"]:
            continue
        results.append({
            "company": name,
            "entity": rec["EntityType"],
            "state": rec["StateCode"],
            "gross_income": rec["GrossIncome"],
            "total_tax": r["summary"]["total_tax"],
            "effective_rate": r["summary"]["effective_rate"],
        })
    return {"count": len(results), "results": results}


def explain_tax_rule(rule: str) -> dict[str, Any]:
    """Static knowledge base of the tax rules used in this engine."""
    rules = {
        "qbi": {
            "name": "QBI (Qualified Business Income) Deduction",
            "summary": "20% deduction on Federal Taxable Income for pass-through entities (S-Corp, LLC, Partnership). C-Corps do not qualify.",
            "applies_to": "S-Corp, LLC, Partnership",
            "formula": "QBI = 20% * Federal Taxable Income; Adjusted Taxable = Federal Taxable - QBI",
        },
        "nol": {
            "name": "NOL (Net Operating Loss) Carryforward",
            "summary": "Post-TCJA: NOL usage is capped at 80% of taxable income (after QBI adjustment).",
            "formula": "NOL Used = min(NOLCarryforward, 80% * Adjusted Taxable Income)",
        },
        "ca_minimum": {
            "name": "California Minimum Franchise Tax",
            "summary": "California enforces an $800 minimum franchise tax regardless of computed amount.",
            "formula": "State Tax = max(800, State Taxable * CA Rate)",
        },
        "c_corp_rate": {
            "name": "C-Corp Federal Rate",
            "summary": "Flat 21% federal rate on Final Federal Taxable Income (post-TCJA).",
        },
        "credits": {
            "name": "Tax Credits",
            "summary": "Reduce federal tax only (not state). Cannot make federal tax negative.",
            "formula": "Federal Tax = max(0, Federal Tax - Credits)",
        },
        "state_tax": {
            "name": "State Tax",
            "summary": "Uses pre-QBI taxable income base. Some states (TX, WA, OH) are 0% for all entities; FL is 0% for pass-throughs.",
            "rates": STATE_RATES,
        },
        "brackets": {
            "name": "2024 Pass-Through Federal Brackets",
            "brackets": BRACKETS_2024,
        },
    }
    rule_l = (rule or "").lower().strip()
    for key, val in rules.items():
        if key in rule_l or rule_l in key or rule_l in val["name"].lower():
            return val
    return {"available_rules": list(rules.keys()), "all_rules": rules}


def nol_impact_analysis(company_name: str) -> dict[str, Any]:
    rec = find_company(company_name)
    if not rec:
        return {"error": f"Company not found: {company_name}"}
    with_nol = TAX_RESULTS.get(rec["CompanyName"]) or calculate_tax(rec)
    no_nol = calculate_tax({**rec, "NOLCarryforward": 0})
    savings = no_nol["summary"]["total_tax"] - with_nol["summary"]["total_tax"]
    return {
        "company": rec["CompanyName"],
        "nol_carryforward": rec["NOLCarryforward"],
        "nol_used": with_nol["steps"]["step3_nol_used"],
        "tax_with_nol": with_nol["summary"]["total_tax"],
        "tax_without_nol": no_nol["summary"]["total_tax"],
        "savings_from_nol": round(savings, 2),
    }


def credit_impact_analysis(company_name: str) -> dict[str, Any]:
    rec = find_company(company_name)
    if not rec:
        return {"error": f"Company not found: {company_name}"}
    with_credits = TAX_RESULTS.get(rec["CompanyName"]) or calculate_tax(rec)
    no_credits = calculate_tax({**rec, "Credits": 0})
    savings = no_credits["summary"]["federal_tax"] - with_credits["summary"]["federal_tax"]
    return {
        "company": rec["CompanyName"],
        "credits": rec["Credits"],
        "federal_tax_with_credits": with_credits["summary"]["federal_tax"],
        "federal_tax_without_credits": no_credits["summary"]["federal_tax"],
        "savings_from_credits": round(savings, 2),
    }


def state_comparison(company_name: str) -> dict[str, Any]:
    """Recalculate company across every supported state. Returns sorted list."""
    rec = find_company(company_name)
    if not rec:
        return {"error": f"Company not found: {company_name}"}
    rows = []
    for state in STATE_RATES.keys():
        r = calculate_tax({**rec, "StateCode": state})
        rows.append({
            "state": state,
            "state_tax": r["summary"]["state_tax"],
            "total_tax": r["summary"]["total_tax"],
            "effective_rate": r["summary"]["effective_rate"],
        })
    rows.sort(key=lambda x: x["total_tax"])
    return {
        "company": rec["CompanyName"],
        "current_state": rec["StateCode"],
        "ranked_by_total_tax": rows,
        "best_state": rows[0],
        "worst_state": rows[-1],
    }


def entity_type_comparison(company_name: str) -> dict[str, Any]:
    rec = find_company(company_name)
    if not rec:
        return {"error": f"Company not found: {company_name}"}
    rows = []
    for et in ["C-Corp", "S-Corp", "LLC", "Partnership"]:
        r = calculate_tax({**rec, "EntityType": et})
        rows.append({
            "entity_type": et,
            "federal_tax": r["summary"]["federal_tax"],
            "state_tax": r["summary"]["state_tax"],
            "total_tax": r["summary"]["total_tax"],
            "effective_rate": r["summary"]["effective_rate"],
        })
    rows.sort(key=lambda x: x["total_tax"])
    return {
        "company": rec["CompanyName"],
        "current_entity": rec["EntityType"],
        "ranked_by_total_tax": rows,
        "best_entity": rows[0],
    }


def top_n_analysis(metric: str = "total_tax", n: int = 5, ascending: bool = False) -> dict[str, Any]:
    """metric: 'total_tax' | 'effective_rate' | 'federal_tax' | 'state_tax' | 'gross_income'."""
    valid = {"total_tax", "effective_rate", "federal_tax", "state_tax", "gross_income"}
    if metric not in valid:
        return {"error": f"Invalid metric. Use one of: {valid}"}
    rows = []
    for name, r in TAX_RESULTS.items():
        if metric == "gross_income":
            v = COMPANIES[name]["GrossIncome"]
        else:
            v = r["summary"][metric]
        rows.append({
            "company": name,
            "entity": COMPANIES[name]["EntityType"],
            "state": COMPANIES[name]["StateCode"],
            metric: v,
        })
    rows.sort(key=lambda x: x[metric], reverse=not ascending)
    return {"metric": metric, "ascending": ascending, "top_n": rows[:n]}


def tax_savings_opportunities(threshold_savings: float = 1000.0) -> dict[str, Any]:
    """For each company, find best alternative state and entity type.

    Returns those whose best alternative would save more than threshold.
    """
    opportunities = []
    for name, rec in COMPANIES.items():
        current_total = TAX_RESULTS[name]["summary"]["total_tax"]
        # Best state
        state_results = state_comparison(name)
        best_state = state_results["best_state"]
        state_savings = current_total - best_state["total_tax"]
        # Best entity
        entity_results = entity_type_comparison(name)
        best_entity = entity_results["best_entity"]
        entity_savings = current_total - best_entity["total_tax"]
        max_savings = max(state_savings, entity_savings)
        if max_savings >= threshold_savings:
            opportunities.append({
                "company": name,
                "current_total_tax": current_total,
                "best_state_alternative": best_state,
                "best_entity_alternative": best_entity,
                "max_potential_savings": round(max_savings, 2),
            })
    opportunities.sort(key=lambda x: x["max_potential_savings"], reverse=True)
    return {"count": len(opportunities), "opportunities": opportunities}


def list_all_companies() -> list[dict[str, Any]]:
    return [
        {
            "company": name,
            "entity": COMPANIES[name]["EntityType"],
            "state": COMPANIES[name]["StateCode"],
            "gross_income": COMPANIES[name]["GrossIncome"],
            "total_tax": r["summary"]["total_tax"],
            "effective_rate": r["summary"]["effective_rate"],
        }
        for name, r in TAX_RESULTS.items()
    ]
