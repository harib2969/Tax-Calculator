"""
tax_engine.py — US Sales & Use Tax Calculation Engine
======================================================
STANDALONE MODULE — swap this file out without touching any other code.

Covers:
  • Sales Tax  : seller collects at point of sale
  • Use Tax    : buyer owes when sales tax was NOT collected by seller
  • Nexus      : whether seller is obligated to collect in a given state
  • Exemptions : SaaS, groceries, medical, resale (B2B), no-tax states
  • Economic nexus thresholds (post-Wayfair, 2024)

Input  : TaxInput dataclass
Output : TaxResult dataclass
"""

from dataclasses import dataclass, field
from typing import Optional


# ── State rate table (2024 base state rates, %) ─────────────────────────────
# Local/county rates vary — base state rates used here for estimation.
# Source: Sales Tax Institute / Tax Foundation 2024

STATE_RATES: dict[str, float] = {
    "AL": 4.00, "AK": 0.00, "AZ": 5.60, "AR": 6.50, "CA": 7.25,
    "CO": 2.90, "CT": 6.35, "DE": 0.00, "FL": 6.00, "GA": 4.00,
    "HI": 4.00, "ID": 6.00, "IL": 6.25, "IN": 7.00, "IA": 6.00,
    "KS": 6.50, "KY": 6.00, "LA": 4.45, "ME": 5.50, "MD": 6.00,
    "MA": 6.25, "MI": 6.00, "MN": 6.875,"MS": 7.00, "MO": 4.225,
    "MT": 0.00, "NE": 5.50, "NV": 6.85, "NH": 0.00, "NJ": 6.625,
    "NM": 5.00, "NY": 4.00, "NC": 4.75, "ND": 5.00, "OH": 5.75,
    "OK": 4.50, "OR": 0.00, "PA": 6.00, "RI": 7.00, "SC": 6.00,
    "SD": 4.20, "TN": 7.00, "TX": 6.25, "UT": 4.85, "VT": 6.00,
    "VA": 4.30, "WA": 6.50, "WV": 6.00, "WI": 5.00, "WY": 4.00,
    "DC": 6.00,
}

# States with NO sales tax
NO_TAX_STATES = {"AK", "DE", "MT", "NH", "OR"}

# ── Economic nexus thresholds (post-Wayfair 2024) ───────────────────────────
# (sales_amount_threshold, transaction_count_threshold)
# If EITHER threshold is crossed, nexus is established.
ECONOMIC_NEXUS: dict[str, tuple[int, Optional[int]]] = {
    "AL": (250_000, None),   "AK": (100_000, 200),    "AZ": (100_000, None),
    "AR": (100_000, 200),    "CA": (500_000, None),    "CO": (100_000, None),
    "CT": (100_000, 200),    "FL": (100_000, 200),     "GA": (100_000, 200),
    "HI": (100_000, 200),    "ID": (100_000, None),    "IL": (100_000, 200),
    "IN": (100_000, 200),    "IA": (100_000, None),    "KS": (100_000, None),
    "KY": (100_000, 200),    "LA": (100_000, 200),     "ME": (100_000, 200),
    "MD": (100_000, 200),    "MA": (100_000, None),    "MI": (100_000, 200),
    "MN": (100_000, 200),    "MS": (250_000, None),    "MO": (100_000, None),
    "NE": (100_000, 200),    "NV": (100_000, 200),     "NJ": (100_000, 200),
    "NM": (100_000, None),   "NY": (500_000, 100),     "NC": (100_000, 200),
    "ND": (100_000, 200),    "OH": (100_000, 200),     "OK": (100_000, None),
    "PA": (100_000, None),   "RI": (100_000, 200),     "SC": (100_000, None),
    "SD": (100_000, None),   "TN": (100_000, None),    "TX": (500_000, None),
    "UT": (100_000, 200),    "VT": (100_000, 200),     "VA": (100_000, 200),
    "WA": (100_000, None),   "WV": (100_000, 200),     "WI": (100_000, None),
    "WY": (100_000, 200),    "DC": (100_000, 200),
}

# ── Product taxability rules ─────────────────────────────────────────────────
# States where SaaS is NOT taxable (majority exempt SaaS as of 2024)
SAAS_EXEMPT_STATES = {
    "CA", "CO", "FL", "GA", "ID", "IL", "MA", "MI", "MN",
    "MO", "MT", "NE", "NV", "NJ", "NY", "OH", "OR", "PA",
    "TX", "VA", "WA", "WI",
}

# States where groceries are generally exempt
GROCERY_EXEMPT_STATES = {
    "AZ", "CA", "CO", "CT", "FL", "GA", "ID", "IL", "KS",
    "LA", "MA", "MD", "ME", "MI", "MN", "NC", "NJ", "NM",
    "NV", "NY", "OH", "PA", "RI", "SC", "TX", "VA", "VT",
    "WA", "WI", "WY",
}

# Medical / prescription drugs: broadly exempt in most states
MEDICAL_EXEMPT_STATES = set(STATE_RATES.keys()) - {"IL", "MN"}


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TaxInput:
    sale_amount: float                          # gross sale amount in USD
    state: str                                  # 2-letter state code
    product_type: str = "physical_goods"        # see PRODUCT_TYPES below
    is_use_tax: bool = False                    # True = buyer owes use tax
    business_type: str = "b2c"                  # "b2b" = potential resale exemption
    annual_sales_in_state: float = 0.0          # for nexus check
    annual_transactions_in_state: int = 0       # for nexus check
    has_physical_presence: bool = False         # office, warehouse, employee in state


@dataclass
class NexusDetail:
    has_nexus: bool
    reason: str                                 # human-readable explanation
    threshold_amount: Optional[int] = None
    threshold_transactions: Optional[int] = None


@dataclass
class ExemptionDetail:
    is_exempt: bool
    reason: str


@dataclass
class TaxResult:
    # ── inputs echo ──
    state: str
    sale_amount: float
    product_type: str
    is_use_tax: bool

    # ── nexus ──
    nexus: NexusDetail

    # ── exemption ──
    exemption: ExemptionDetail

    # ── calculation ──
    rate_pct: float                             # state base rate used
    tax_amount: float                           # dollar amount of tax
    total_due: float                            # sale_amount + tax_amount

    # ── metadata ──
    tax_type_label: str                         # "Sales Tax" or "Use Tax"
    state_name: str
    notes: list[str] = field(default_factory=list)


# ── State name lookup ────────────────────────────────────────────────────────
STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia",
    "HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
    "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire",
    "NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina",
    "ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania",
    "RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee",
    "TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
    "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia",
}


# ── Core engine ──────────────────────────────────────────────────────────────

def calculate_sales_use_tax(inp: TaxInput) -> TaxResult:
    """
    Main entry point. Takes a TaxInput and returns a full TaxResult.

    Steps:
      1. Validate & normalize state code
      2. Check nexus (physical presence OR economic threshold)
      3. Check product exemption
      4. Apply rate and compute tax amount
      5. Return structured TaxResult
    """

    state = inp.state.upper().strip()
    notes: list[str] = []

    # ── Step 1: State validation ─────────────────────────────────────────────
    if state not in STATE_RATES:
        raise ValueError(f"Unknown state code: '{state}'. Use 2-letter US state abbreviation.")

    # ── Step 2: Nexus determination ──────────────────────────────────────────
    nexus = _determine_nexus(state, inp)

    # ── Step 3: No-tax states ────────────────────────────────────────────────
    if state in NO_TAX_STATES:
        rate = 0.0
        exemption = ExemptionDetail(
            is_exempt=True,
            reason=f"{STATE_NAMES.get(state, state)} has no state sales tax."
        )
        tax_amount = 0.0
        notes.append("Local jurisdiction taxes may still apply in some areas — verify locally.")
        return TaxResult(
            state=state, sale_amount=inp.sale_amount, product_type=inp.product_type,
            is_use_tax=inp.is_use_tax, nexus=nexus, exemption=exemption,
            rate_pct=0.0, tax_amount=0.0,
            total_due=inp.sale_amount,
            tax_type_label="Use Tax" if inp.is_use_tax else "Sales Tax",
            state_name=STATE_NAMES.get(state, state),
            notes=notes,
        )

    # ── Step 4: Product exemption check ─────────────────────────────────────
    exemption = _determine_exemption(state, inp, notes)

    # ── Step 5: Rate & amount ────────────────────────────────────────────────
    rate = STATE_RATES[state] if not exemption.is_exempt else 0.0
    tax_amount = round(inp.sale_amount * rate / 100, 2)

    # B2B resale note
    if inp.business_type == "b2b" and not exemption.is_exempt:
        notes.append("B2B sale — request a resale exemption certificate (Form ST-8 or state equivalent) to avoid collecting tax on qualified resale purchases.")

    # Use tax note
    if inp.is_use_tax:
        notes.append(f"Use tax of {rate}% is owed by the buyer to {STATE_NAMES.get(state, state)} since sales tax was not collected at point of sale.")

    # Nexus warning if no nexus
    if not nexus.has_nexus:
        notes.append("No nexus established — you are NOT required to collect sales tax in this state today, but monitor your sales volume against the economic nexus threshold.")

    return TaxResult(
        state=state,
        sale_amount=inp.sale_amount,
        product_type=inp.product_type,
        is_use_tax=inp.is_use_tax,
        nexus=nexus,
        exemption=exemption,
        rate_pct=rate,
        tax_amount=tax_amount,
        total_due=round(inp.sale_amount + tax_amount, 2),
        tax_type_label="Use Tax" if inp.is_use_tax else "Sales Tax",
        state_name=STATE_NAMES.get(state, state),
        notes=notes,
    )


# ── Helper: nexus ─────────────────────────────────────────────────────────────

def _determine_nexus(state: str, inp: TaxInput) -> NexusDetail:
    # Physical presence always creates nexus
    if inp.has_physical_presence:
        return NexusDetail(
            has_nexus=True,
            reason="Physical presence nexus (office, warehouse, or employee in state)."
        )

    # No-tax states — nexus concept is moot
    if state in NO_TAX_STATES:
        return NexusDetail(has_nexus=False, reason=f"{state} has no sales tax — nexus not applicable.")

    threshold = ECONOMIC_NEXUS.get(state)
    if not threshold:
        return NexusDetail(has_nexus=False, reason="State economic nexus threshold not found — verify manually.")

    amount_threshold, txn_threshold = threshold

    amount_nexus = inp.annual_sales_in_state >= amount_threshold
    txn_nexus    = txn_threshold is not None and inp.annual_transactions_in_state >= txn_threshold

    if amount_nexus or txn_nexus:
        reason_parts = []
        if amount_nexus:
            reason_parts.append(f"annual sales ${inp.annual_sales_in_state:,.0f} ≥ ${amount_threshold:,.0f} threshold")
        if txn_nexus:
            reason_parts.append(f"{inp.annual_transactions_in_state} transactions ≥ {txn_threshold} threshold")
        return NexusDetail(
            has_nexus=True,
            reason=f"Economic nexus established: {' and '.join(reason_parts)}.",
            threshold_amount=amount_threshold,
            threshold_transactions=txn_threshold,
        )

    return NexusDetail(
        has_nexus=False,
        reason=f"Below economic nexus threshold (${amount_threshold:,.0f} in sales" +
               (f" or {txn_threshold} transactions" if txn_threshold else "") + ").",
        threshold_amount=amount_threshold,
        threshold_transactions=txn_threshold,
    )


# ── Helper: exemption ─────────────────────────────────────────────────────────

def _determine_exemption(state: str, inp: TaxInput, notes: list[str]) -> ExemptionDetail:
    pt = inp.product_type.lower()

    if pt == "saas":
        if state in SAAS_EXEMPT_STATES:
            return ExemptionDetail(True, f"SaaS is not taxable in {STATE_NAMES.get(state, state)} as of 2024.")
        notes.append("SaaS taxability varies — some states treat it as taxable software. Verify current statute.")
        return ExemptionDetail(False, f"SaaS is taxable in {STATE_NAMES.get(state, state)}.")

    if pt == "software":
        # Downloaded software taxable in most states
        return ExemptionDetail(False, "Downloaded/prewritten software is taxable in most states.")

    if pt == "groceries":
        if state in GROCERY_EXEMPT_STATES:
            return ExemptionDetail(True, f"Groceries are exempt from sales tax in {STATE_NAMES.get(state, state)}.")
        return ExemptionDetail(False, f"Groceries are taxable in {STATE_NAMES.get(state, state)}.")

    if pt == "medical":
        if state in MEDICAL_EXEMPT_STATES:
            return ExemptionDetail(True, "Prescription drugs and most medical items are tax-exempt.")
        return ExemptionDetail(False, f"Medical items may be taxable in {STATE_NAMES.get(state, state)} — verify.")

    if pt == "services":
        # Services are generally NOT taxable (only ~5 states broadly tax services)
        taxable_service_states = {"HI", "NM", "SD", "WV", "ND"}
        if state in taxable_service_states:
            return ExemptionDetail(False, f"Services are broadly taxable in {STATE_NAMES.get(state, state)}.")
        return ExemptionDetail(True, f"Services are generally NOT subject to sales tax in {STATE_NAMES.get(state, state)}.")

    # physical_goods / other — taxable by default
    return ExemptionDetail(False, "Physical goods are subject to sales tax.")
