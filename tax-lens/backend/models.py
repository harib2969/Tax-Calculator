"""All Pydantic models in one file for easy copy-paste."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class Company(BaseModel):
    CompanyName: str
    GrossIncome: float
    Deductions: float
    EntityType: str
    StateCode: str
    TaxYear: int = 2024
    NOLCarryforward: float = 0
    EstimatedPayments: float = 0
    Credits: float = 0


class TaxSteps(BaseModel):
    step1_federal_taxable_income: float
    step2_qbi_deduction: float
    step2_adjusted_taxable: float
    step3_nol_used: float
    step3_final_taxable: float
    step4_federal_tax_pre_credits: float
    step5_federal_tax: float
    step6_state_taxable: float
    step6_state_rate: float
    step6_state_tax: float
    step7_total_tax: float
    step7_effective_rate: float


class TaxSummary(BaseModel):
    federal_tax: float
    state_tax: float
    total_tax: float
    effective_rate: float
    estimated_payments: float = 0
    balance_due: float = 0


class TaxResult(BaseModel):
    company: str
    inputs: dict[str, Any]
    steps: TaxSteps
    summary: TaxSummary
    explanation: list[str] = Field(default_factory=list)


class WhatIfRequest(BaseModel):
    company_name: str
    overrides: dict[str, Any] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    company_names: list[str]


class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant' | 'tool' | 'system'
    content: str
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls_made: list[str] = Field(default_factory=list)
    history_length: int = 0
