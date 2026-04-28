"""
providers/llm/azure_openai_adapter.py
Calls Azure OpenAI (GPT-4.5) for NLU extraction + summary generation.
"""

import os, json, logging
from openai import AzureOpenAI
from providers.base import LLMAdapter

log = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a US Sales & Use Tax data extractor.
Extract tax-relevant fields from the query below and return ONLY a valid JSON object — no markdown, no explanation.

Query: "{query}"

Return this exact shape (use null for anything not mentioned):
{{
  "sale_amount": <number or null>,
  "state": <2-letter US state code or null>,
  "product_type": <"physical_goods" | "software" | "saas" | "services" | "groceries" | "medical" | "other">,
  "is_use_tax": <true if buyer owes use tax because no sales tax was collected, else false>,
  "business_type": <"b2b" | "b2c">,
  "has_physical_presence": <true if seller has office/warehouse/employee in that state, else false>,
  "annual_sales_in_state": <number — annual sales to that state, or 0>,
  "annual_transactions_in_state": <number — annual transaction count to that state, or 0>,
  "notes": "<one sentence describing what you found>"
}}

Rules:
- "saas" = software-as-a-service, subscriptions, cloud software
- "services" = consulting, labor, professional services
- If someone says "I bought X from an out-of-state seller without paying tax" → is_use_tax = true
- If someone mentions resale, wholesale, exempt certificate → business_type = b2b
- Return ONLY the JSON object."""

SUMMARY_PROMPT = """You are a friendly, knowledgeable US Sales & Use Tax advisor.
Write 2–3 conversational sentences (no bullet points, no headers).
Cover: what tax applies and why, any exemption, and one practical tip.
Use **bold** for dollar amounts and key terms. Keep it under 80 words.

Tax result:
- State: {state_name}
- Sale amount: ${sale_amount:,.2f}
- Product type: {product_type}
- Tax type: {tax_type}
- Rate: {rate}%
- Tax owed: ${tax_amount:,.2f}
- Exempt: {exempt} ({exempt_reason})
- Nexus: {nexus} ({nexus_reason})"""


class AzureOpenAIAdapter(LLMAdapter):
    def __init__(self):
        self.client = AzureOpenAI(
            api_key        = os.environ["AZURE_OPENAI_KEY"],
            api_version    = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"],
        )
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.5")

    def _call(self, prompt: str, max_tokens: int = 500, temperature: float = 0) -> str:
        resp = self.client.chat.completions.create(
            model       = self.deployment,
            messages    = [{"role": "user", "content": prompt}],
            max_tokens  = max_tokens,
            temperature = temperature,
        )
        return resp.choices[0].message.content.strip()

    def extract(self, user_query: str) -> dict:
        raw = self._call(EXTRACT_PROMPT.format(query=user_query))
        # Strip accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            log.error(f"LLM returned invalid JSON: {raw}")
            raise ValueError(f"LLM extraction failed: {e}")

    def summarize(self, result: dict) -> str:
        prompt = SUMMARY_PROMPT.format(
            state_name   = result.get("state_name", result.get("state", "unknown")),
            sale_amount  = result.get("sale_amount", 0),
            product_type = result.get("product_type", "goods"),
            tax_type     = result.get("tax_type_label", "Sales Tax"),
            rate         = result.get("rate_pct", 0),
            tax_amount   = result.get("tax_amount", 0),
            exempt       = result.get("is_exempt", False),
            exempt_reason= result.get("exemption_reason", ""),
            nexus        = result.get("has_nexus", True),
            nexus_reason = result.get("nexus_reason", ""),
        )
        return self._call(prompt, max_tokens=200, temperature=0.3)
