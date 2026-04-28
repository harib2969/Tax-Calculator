import json
import os
import re

from openai import AzureOpenAI
from pydantic import ValidationError

from .models import FilingStatus, ParsedTaxInput, TaxType


STATE_NAMES = {
    "alabama": "AL",
    "arizona": "AZ",
    "california": "CA",
    "colorado": "CO",
    "florida": "FL",
    "georgia": "GA",
    "illinois": "IL",
    "massachusetts": "MA",
    "new york": "NY",
    "texas": "TX",
    "washington": "WA",
}


def parse_natural_language(query: str) -> ParsedTaxInput:
    genai_parsed = _parse_with_azure_openai(query)
    if genai_parsed:
        return genai_parsed
    return _parse_with_regex(query)


def _parse_with_regex(query: str) -> ParsedTaxInput:
    text = query.lower()
    tax_type = TaxType.SALES_USE if any(term in text for term in ["sales tax", "use tax", "purchase", "shipped"]) else TaxType.FEDERAL

    if tax_type == TaxType.FEDERAL:
        parsed = ParsedTaxInput(
            tax_type=tax_type,
            filing_status=_extract_filing_status(text) or FilingStatus.SINGLE,
            gross_income=_extract_money_after(text, ["income", "earning", "earn", "salary", "wages"]),
            deductions=_extract_money_after(text, ["deduction", "deductions", "itemized"]),
            credits=_extract_money_after(text, ["credit", "credits"]) or 0,
            is_use_tax=False,
        )
        if parsed.filing_status is None:
            parsed.filing_status = FilingStatus.SINGLE
        if parsed.gross_income is None:
            parsed.missing_fields.append("gross_income")
    else:
        parsed = ParsedTaxInput(
            tax_type=tax_type,
            purchase_amount=_extract_money_after(text, ["purchase", "price", "cost", "amount", "laptop", "order"]),
            state=_extract_state(text),
            is_use_tax="use tax" in text,
        )
        if parsed.purchase_amount is None:
            parsed.missing_fields.append("purchase_amount")
        if parsed.state is None:
            parsed.missing_fields.append("state")

    parsed.confidence = 0.9 if not parsed.missing_fields else 0.55
    return parsed


def _parse_with_azure_openai(query: str) -> ParsedTaxInput | None:
    client = _client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not client or not deployment:
        return None

    try:
        response = client.chat.completions.create(
            model=deployment,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured tax-estimate inputs from the user's question. "
                        "Return only JSON with these keys: tax_type, filing_status, gross_income, "
                        "deductions, credits, purchase_amount, state, is_use_tax, confidence, missing_fields. "
                        "tax_type must be 'federal' or 'sales_use'. filing_status must be one of "
                        "'single', 'married_filing_jointly', 'married_filing_separately', "
                        "'head_of_household', or null. state must be a two-letter uppercase US state code "
                        "or null. Use numbers only for money fields, with no commas or symbols. "
                        "If the user asks sales tax or use tax, set tax_type to 'sales_use'. "
                        "If the user asks federal income tax and filing status is missing, default to 'single'. "
                        "Put missing required fields in missing_fields. Required federal field: gross_income. "
                        "Required sales/use fields: purchase_amount and state."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=350,
        )
        content = response.choices[0].message.content
        if not content:
            return None
        payload = json.loads(content)
        parsed = ParsedTaxInput.model_validate(payload)
        return _finalize_generated_parse(parsed)
    except (json.JSONDecodeError, ValidationError, Exception):
        return None


def _client() -> AzureOpenAI | None:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not endpoint or not api_key:
        return None
    return AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)


def _finalize_generated_parse(parsed: ParsedTaxInput) -> ParsedTaxInput:
    parsed.missing_fields = []
    if parsed.state:
        parsed.state = parsed.state.upper()

    if parsed.tax_type == TaxType.FEDERAL:
        parsed.filing_status = parsed.filing_status or FilingStatus.SINGLE
        parsed.purchase_amount = None
        parsed.state = None
        parsed.is_use_tax = False
        if parsed.gross_income is None:
            parsed.missing_fields.append("gross_income")
    else:
        parsed.filing_status = None
        parsed.gross_income = None
        parsed.deductions = None
        parsed.credits = 0
        if parsed.purchase_amount is None:
            parsed.missing_fields.append("purchase_amount")
        if parsed.state is None:
            parsed.missing_fields.append("state")

    parsed.confidence = parsed.confidence or (0.9 if not parsed.missing_fields else 0.55)
    return parsed


def _extract_filing_status(text: str) -> FilingStatus | None:
    if "married filing jointly" in text or "mfj" in text or "married jointly" in text:
        return FilingStatus.MARRIED_FILING_JOINTLY
    if "married filing separately" in text or "mfs" in text:
        return FilingStatus.MARRIED_FILING_SEPARATELY
    if "head of household" in text or "hoh" in text:
        return FilingStatus.HEAD_OF_HOUSEHOLD
    if "single" in text:
        return FilingStatus.SINGLE
    return None


def _extract_state(text: str) -> str | None:
    for name, code in STATE_NAMES.items():
        if name in text:
            return code
    match = re.search(r"\b(AL|AZ|CA|CO|FL|GA|IL|MA|NY|TX|WA)\b", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _extract_money_after(text: str, labels: list[str]) -> float | None:
    money_pattern = r"\$?\s*([0-9][0-9,]*(?:\.\d+)?)(\s*k)?"
    for label in labels:
        after_label = re.search(label + r"[^0-9$]{0,25}" + money_pattern, text)
        if after_label:
            return _to_number(after_label.group(1), after_label.group(2))
        before_label = re.search(money_pattern + r"[^a-z0-9$]{0,25}" + label, text)
        if before_label:
            return _to_number(before_label.group(1), before_label.group(2))

    all_amounts = re.findall(money_pattern, text)
    if len(all_amounts) == 1:
        return _to_number(all_amounts[0][0], all_amounts[0][1])
    return None


def _to_number(raw: str, suffix: str | None) -> float:
    value = float(raw.replace(",", ""))
    return value * 1000 if suffix and suffix.strip() == "k" else value
