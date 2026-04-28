import os

from openai import AzureOpenAI

from .models import ParsedTaxInput, TaxEstimate


def generate_summary(query: str, parsed: ParsedTaxInput, estimate: TaxEstimate) -> str:
    client = _client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not client or not deployment:
        return _fallback_summary(parsed, estimate)

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": "You explain demo tax estimates in plain English. Be concise and include a reminder that this is not tax advice.",
            },
            {
                "role": "user",
                "content": f"Original query: {query}\nParsed input: {parsed.model_dump()}\nEstimate: {estimate.model_dump()}",
            },
        ],
        temperature=0.2,
        max_tokens=220,
    )
    return response.choices[0].message.content or _fallback_summary(parsed, estimate)


def _client() -> AzureOpenAI | None:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not endpoint or not api_key:
        return None
    return AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)


def _fallback_summary(parsed: ParsedTaxInput, estimate: TaxEstimate) -> str:
    if parsed.tax_type.value == "federal":
        status = estimate.details.get("filing_status", "single")
        return (
            f"Using demo 2025 federal brackets for {status}, taxable income is "
            f"${estimate.taxable_amount:,.2f} and estimated federal tax is ${estimate.estimated_tax:,.2f}. "
            f"The effective rate is {estimate.effective_rate:.2%}. This is a planning estimate, not tax advice."
        )
    label = "use tax" if parsed.is_use_tax else "sales tax"
    return (
        f"Using the demo state-level rate for {parsed.state}, estimated {label} is "
        f"${estimate.estimated_tax:,.2f} on ${estimate.taxable_amount:,.2f}. Local rates are not included."
    )

