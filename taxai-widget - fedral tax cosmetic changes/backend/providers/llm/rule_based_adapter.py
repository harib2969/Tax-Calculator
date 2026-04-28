"""
providers/llm/rule_based_adapter.py
Zero-dependency NLP fallback — regex + keyword matching.
Activates automatically when no LLM API key is present.
"""

import re
from providers.base import LLMAdapter

_STATES = {
    "AL":"alabama","AK":"alaska","AZ":"arizona","AR":"arkansas","CA":"california",
    "CO":"colorado","CT":"connecticut","DE":"delaware","FL":"florida","GA":"georgia",
    "HI":"hawaii","ID":"idaho","IL":"illinois","IN":"indiana","IA":"iowa",
    "KS":"kansas","KY":"kentucky","LA":"louisiana","ME":"maine","MD":"maryland",
    "MA":"massachusetts","MI":"michigan","MN":"minnesota","MS":"mississippi",
    "MO":"missouri","MT":"montana","NE":"nebraska","NV":"nevada","NH":"new hampshire",
    "NJ":"new jersey","NM":"new mexico","NY":"new york","NC":"north carolina",
    "ND":"north dakota","OH":"ohio","OK":"oklahoma","OR":"oregon","PA":"pennsylvania",
    "RI":"rhode island","SC":"south carolina","SD":"south dakota","TN":"tennessee",
    "TX":"texas","UT":"utah","VT":"vermont","VA":"virginia","WA":"washington",
    "WV":"west virginia","WI":"wisconsin","WY":"wyoming","DC":"district of columbia",
}

class RuleBasedAdapter(LLMAdapter):

    def extract(self, query: str) -> dict:
        t = query.lower()

        # ── Amount ──────────────────────────────────────────────────────────
        amount = None
        for pat, mult in [
            (r'\$\s*([\d,]+\.?\d*)\s*million', 1_000_000),
            (r'\$\s*([\d,]+\.?\d*)\s*k\b',     1_000),
            (r'\$\s*([\d,]+\.?\d*)',             1),
            (r'([\d,]+\.?\d*)\s*dollar',         1),
        ]:
            m = re.search(pat, t)
            if m:
                amount = float(m.group(1).replace(",", "")) * mult
                break

        # ── State ────────────────────────────────────────────────────────────
        state = None
        words = re.sub(r'[^\w\s]', '', t).split()
        for code, name in _STATES.items():
            if code.lower() in words or name in t:
                state = code
                break

        # ── Product type ─────────────────────────────────────────────────────
        product = "physical_goods"
        if any(w in t for w in ["saas", "software as a service", "subscription", "cloud"]):
            product = "saas"
        elif any(w in t for w in ["software", "app ", "download", "license"]):
            product = "software"
        elif any(w in t for w in ["service", "consulting", "labor", "repair", "professional"]):
            product = "services"
        elif any(w in t for w in ["grocery", "groceries", "food", "produce"]):
            product = "groceries"
        elif any(w in t for w in ["medicine", "medication", "prescription", "medical", "drug"]):
            product = "medical"

        # ── Use tax ──────────────────────────────────────────────────────────
        use_tax = any(w in t for w in [
            "use tax", "didn't pay", "did not pay", "no sales tax",
            "out of state", "online purchase", "bought from", "purchased from"
        ])

        # ── B2B ──────────────────────────────────────────────────────────────
        b2b = "b2b" if any(w in t for w in [
            "resale", "wholesale", "exempt certificate", "b2b", "business purchase", "for resale"
        ]) else "b2c"

        # ── Physical presence ────────────────────────────────────────────────
        physical = any(w in t for w in [
            "office", "warehouse", "employee", "store", "location", "based in", "incorporated in"
        ])

        return {
            "sale_amount": amount,
            "state": state,
            "product_type": product,
            "is_use_tax": use_tax,
            "business_type": b2b,
            "has_physical_presence": physical,
            "annual_sales_in_state": 0,
            "annual_transactions_in_state": 0,
            "notes": (
                f"Rule-based extraction: {product}"
                + (f" · ${amount:,.0f}" if amount else "")
                + (f" · {state}" if state else " · state not detected")
            ),
        }

    def summarize(self, result: dict) -> str:
        state    = result.get("state_name", result.get("state", "your state"))
        rate     = result.get("rate_pct", 0)
        tax_amt  = result.get("tax_amount", 0)
        exempt   = result.get("is_exempt", False)
        nexus    = result.get("has_nexus", True)

        if exempt:
            reason = result.get("exemption_reason", "product type")
            return (f"This transaction is **exempt** from sales tax in **{state}** based on {reason}. "
                    "Retain documentation of the exemption in case of audit.")
        if not nexus:
            return (f"You don't have nexus in **{state}** yet, so you're **not required** to collect sales tax there. "
                    "Monitor your sales volume — once you cross the economic nexus threshold, registration is required.")
        return (f"**{state}** has a **{rate}%** state sales tax rate on this transaction. "
                f"Estimated tax owed: **${tax_amt:,.2f}**. "
                "Keep a record of the sale date, product category, and customer location for compliance.")
