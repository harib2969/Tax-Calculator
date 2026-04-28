from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class TaxType(StrEnum):
    FEDERAL = "federal"
    SALES_USE = "sales_use"


class FilingStatus(StrEnum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


class EstimateRequest(BaseModel):
    query: str = Field(..., min_length=5, examples=["Estimate federal tax for single filer earning $120,000."])
    save: bool = True


class ParsedTaxInput(BaseModel):
    tax_type: TaxType
    filing_status: FilingStatus | None = None
    gross_income: float | None = None
    deductions: float | None = None
    credits: float = 0
    purchase_amount: float | None = None
    state: str | None = None
    is_use_tax: bool = False
    confidence: float = 0.65
    missing_fields: list[str] = Field(default_factory=list)


class TaxEstimate(BaseModel):
    tax_type: TaxType
    taxable_amount: float
    estimated_tax: float
    effective_rate: float
    marginal_rate: float | None = None
    details: dict


class EstimateResponse(BaseModel):
    parsed_input: ParsedTaxInput
    estimate: TaxEstimate
    summary: str
    disclaimer: str
    saved: bool = False
    storage_status: Literal["skipped", "saved", "not_configured", "failed"] = "skipped"

