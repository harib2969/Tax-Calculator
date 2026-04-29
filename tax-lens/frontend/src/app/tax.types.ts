export interface Company {
  CompanyName: string;
  GrossIncome: number;
  Deductions: number;
  EntityType: 'C-Corp' | 'S-Corp' | 'LLC' | 'Partnership' | string;
  StateCode: string;
  TaxYear: number;
  NOLCarryforward: number;
  EstimatedPayments: number;
  Credits: number;
}

export interface CompanySummaryRow {
  company: string;
  entity: string;
  state: string;
  gross_income: number;
  total_tax: number;
  effective_rate: number;
  federal_tax?: number;
  state_tax?: number;
}

export interface TaxSteps {
  step1_federal_taxable_income: number;
  step2_qbi_deduction: number;
  step2_adjusted_taxable: number;
  step3_nol_used: number;
  step3_final_taxable: number;
  step4_federal_tax_pre_credits: number;
  step5_federal_tax: number;
  step6_state_taxable: number;
  step6_state_rate: number;
  step6_state_tax: number;
  step7_total_tax: number;
  step7_effective_rate: number;
}

export interface TaxSummary {
  federal_tax: number;
  state_tax: number;
  total_tax: number;
  effective_rate: number;
  estimated_payments?: number;
  balance_due?: number;
}

export interface TaxBreakdown {
  company: string;
  inputs: Company;
  steps: TaxSteps;
  summary: TaxSummary;
  explanation: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: string[];
  ts: number;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  tool_calls_made: string[];
  history_length: number;
}
