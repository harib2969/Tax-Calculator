"""
Azure OpenAI integration with function calling (13 agentic tools).

The LLM never computes tax. It picks tools, we run them deterministically,
hand the JSON result back, and let the LLM compose a natural-language answer.
"""
import json
import os
from typing import Any

from openai import AzureOpenAI

import tax_engine

# ──────────────────────────────────────────────────────────────────────────────
# Azure OpenAI client (configured from .env)
# ──────────────────────────────────────────────────────────────────────────────
_client: AzureOpenAI | None = None
_deployment: str = ""


def init_azure_openai() -> str:
    """Initialize Azure OpenAI client from environment variables."""
    global _client, _deployment
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    key = os.getenv("AZURE_OPENAI_KEY", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    _deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    if not (endpoint and key and _deployment):
        return "NOT configured — set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT in .env"
    _client = AzureOpenAI(api_key=key, api_version=api_version, azure_endpoint=endpoint)
    return f"Azure OpenAI configured (deployment={_deployment}, api_version={api_version})"


# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — defines persona, tone, and tool-use discipline
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Tax Lens, an expert U.S. corporate tax advisor for the 2024 tax year.

YOUR PURPOSE
You explain, justify, and explore tax calculations for a portfolio of companies.
You ALWAYS call tools to get numbers. You NEVER compute tax math yourself in your head —
the deterministic tax engine is the only source of truth.

TONE & STYLE
• Plain, conversational language with precise tax terminology where it adds value.
• Default to concise answers (2-5 sentences). Expand to numbered step-by-step breakdowns
  when the user asks "why", "how", "explain", or challenges a calculation.
• When you cite a number, say where it came from (e.g., "step 4 federal computation").
• Be proactive: if a user asks about Pacific Manufacturing in CA, mention if a different
  state would save them significant tax.
• If the user is ambiguous (e.g., "Pacific"), ask which one or pick the closest match.

TAX ENGINE RULES (you should know these — but never compute, always call tools)
1. Federal Taxable Income = max(0, Gross Income - Deductions)
2. QBI: 20% deduction for pass-throughs (S-Corp, LLC, Partnership) only. C-Corps skip.
3. NOL: capped at 80% of post-QBI taxable income.
4. Federal tax: C-Corps flat 21%; pass-throughs use 2024 individual brackets.
5. Credits reduce federal tax only; floored at $0 (no refunds).
6. State tax uses pre-QBI base × state rate. CA has $800 minimum franchise tax.
   TX/WA/OH = 0% all entities; FL pass-throughs = 0%.
7. Total Tax = Federal + State; Effective Rate = Total / Gross × 100.

WHEN A USER CHALLENGES A CALCULATION
1. Call get_company_tax_breakdown to get the authoritative steps.
2. Walk through each relevant step that affects their question.
3. If they suggest a different approach, run what_if_calculator to show the comparison.
4. Stand behind the math — but acknowledge legitimate strategy questions
   (e.g., "your deductions look low — would you like to model higher deductions?").

SESSION CONTINUITY
You have full conversation history. If the user said "this company" they mean the most
recent company discussed. If they said "what if it was an LLC?", apply the override to
the company already in context.

TOOL USAGE
Always prefer tools over guessing. If multiple tools are needed, call them in parallel
when possible (e.g., compare_companies + state_comparison for a full picture).
"""


# ──────────────────────────────────────────────────────────────────────────────
# 13 AGENTIC TOOL DEFINITIONS (OpenAI function-calling format)
# ──────────────────────────────────────────────────────────────────────────────
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_company_tax_breakdown",
            "description": "Get the full 7-step deterministic tax breakdown for a single company. Returns inputs, every intermediate step, summary totals, and a human-readable explanation array.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Company name. Fuzzy/partial match supported."}
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "what_if_calculator",
            "description": "Recalculate a company's tax with one or more overrides applied. Use for ANY override: state, entity type, deductions, gross income, credits, NOL, etc. Returns original vs modified side-by-side.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "overrides": {
                        "type": "object",
                        "description": "Any subset of: GrossIncome, Deductions, EntityType (C-Corp/S-Corp/LLC/Partnership), StateCode (CA/NY/TX/FL/IL/WA/PA/OH/MA/NJ), NOLCarryforward, Credits, EstimatedPayments.",
                        "additionalProperties": True,
                    },
                },
                "required": ["company_name", "overrides"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recalculate_with_overrides",
            "description": "Apply MULTIPLE overrides at once (e.g., new state + new entity + new deductions). Same engine as what_if_calculator; semantically clearer for chained scenarios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "overrides": {"type": "object", "additionalProperties": True},
                },
                "required": ["company_name", "overrides"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_companies",
            "description": "Compare 2 or more companies side-by-side on every key tax metric.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_names": {"type": "array", "items": {"type": "string"}, "minItems": 2}
                },
                "required": ["company_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "portfolio_analysis",
            "description": "Cross-portfolio insights: total tax burden, highest/lowest payers, best/worst effective rates across ALL companies.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_companies",
            "description": "Filter portfolio by entity type, state, gross income range, or total tax range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {"type": "string", "enum": ["C-Corp", "S-Corp", "LLC", "Partnership"]},
                            "state": {"type": "string"},
                            "min_gross": {"type": "number"},
                            "max_gross": {"type": "number"},
                            "min_total_tax": {"type": "number"},
                            "max_total_tax": {"type": "number"},
                        },
                    }
                },
                "required": ["filters"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_tax_rule",
            "description": "Explain a tax rule used in this engine: 'qbi', 'nol', 'ca_minimum', 'c_corp_rate', 'credits', 'state_tax', 'brackets'.",
            "parameters": {
                "type": "object",
                "properties": {"rule": {"type": "string"}},
                "required": ["rule"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nol_impact_analysis",
            "description": "How much tax is the company saving thanks to NOL carryforward? Compares with-NOL vs without-NOL.",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "credit_impact_analysis",
            "description": "How much federal tax do credits save this company? Compares with-credits vs without.",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "state_comparison",
            "description": "Recalculate the company across all 10 supported states. Returns ranked list with best/worst.",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "entity_type_comparison",
            "description": "Recalculate the company as each of the 4 entity types. Returns ranked list with the most tax-efficient structure.",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_n_analysis",
            "description": "Top N companies by a metric. Metrics: total_tax, effective_rate, federal_tax, state_tax, gross_income.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["total_tax", "effective_rate", "federal_tax", "state_tax", "gross_income"]},
                    "n": {"type": "integer", "default": 5},
                    "ascending": {"type": "boolean", "default": False},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tax_savings_opportunities",
            "description": "Identify portfolio-wide restructuring opportunities. For each company, finds the best alternative state and entity type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_savings": {"type": "number", "default": 1000, "description": "Minimum savings (USD) to qualify as an opportunity."}
                },
            },
        },
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# TOOL DISPATCHER — maps tool name -> tax_engine function
# ──────────────────────────────────────────────────────────────────────────────
def _dispatch(name: str, args: dict[str, Any]) -> Any:
    if name == "get_company_tax_breakdown":
        return tax_engine.get_company_tax_breakdown(args["company_name"])
    if name == "what_if_calculator":
        return tax_engine.what_if_calculator(args["company_name"], args.get("overrides", {}))
    if name == "recalculate_with_overrides":
        return tax_engine.recalculate_with_overrides(args["company_name"], args.get("overrides", {}))
    if name == "compare_companies":
        return tax_engine.compare_companies(args["company_names"])
    if name == "portfolio_analysis":
        return tax_engine.portfolio_analysis()
    if name == "filter_companies":
        return tax_engine.filter_companies(args.get("filters", {}))
    if name == "explain_tax_rule":
        return tax_engine.explain_tax_rule(args.get("rule", ""))
    if name == "nol_impact_analysis":
        return tax_engine.nol_impact_analysis(args["company_name"])
    if name == "credit_impact_analysis":
        return tax_engine.credit_impact_analysis(args["company_name"])
    if name == "state_comparison":
        return tax_engine.state_comparison(args["company_name"])
    if name == "entity_type_comparison":
        return tax_engine.entity_type_comparison(args["company_name"])
    if name == "top_n_analysis":
        return tax_engine.top_n_analysis(
            args.get("metric", "total_tax"),
            int(args.get("n", 5)),
            bool(args.get("ascending", False)),
        )
    if name == "tax_savings_opportunities":
        return tax_engine.tax_savings_opportunities(float(args.get("threshold_savings", 1000.0)))
    return {"error": f"Unknown tool: {name}"}


# ──────────────────────────────────────────────────────────────────────────────
# CHAT TURN — full agentic loop with tool calls
# ──────────────────────────────────────────────────────────────────────────────
def chat_turn(history: list[dict[str, Any]], user_message: str, max_tool_iters: int = 5) -> dict[str, Any]:
    """Run one full chat turn.

    Args:
        history: prior messages in OpenAI format (role/content/tool_calls/tool_call_id)
        user_message: the new user input

    Returns:
        {
          'reply': final assistant text,
          'tool_calls_made': [tool names in order],
          'new_messages': [messages to append to session history]
        }
    """
    if _client is None:
        return {
            "reply": ("Azure OpenAI is not configured. Please set AZURE_OPENAI_ENDPOINT, "
                      "AZURE_OPENAI_KEY, and AZURE_OPENAI_DEPLOYMENT in backend/.env "
                      "and restart the server."),
            "tool_calls_made": [],
            "new_messages": [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": "(AI not configured)"},
            ],
        }

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    new_messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    tool_calls_made: list[str] = []

    for _ in range(max_tool_iters):
        response = _client.chat.completions.create(
            model=_deployment,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
            messages.append(assistant_msg)
            new_messages.append(assistant_msg)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                tool_calls_made.append(fn_name)
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = _dispatch(fn_name, args)
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": json.dumps(result, default=str),
                }
                messages.append(tool_msg)
                new_messages.append(tool_msg)
            continue

        # No more tool calls — final answer
        final_msg = {"role": "assistant", "content": msg.content or ""}
        messages.append(final_msg)
        new_messages.append(final_msg)
        return {
            "reply": msg.content or "",
            "tool_calls_made": tool_calls_made,
            "new_messages": new_messages,
        }

    # Hit max iterations — return whatever we have
    return {
        "reply": "(Reached max tool iterations — please rephrase your question.)",
        "tool_calls_made": tool_calls_made,
        "new_messages": new_messages,
    }
