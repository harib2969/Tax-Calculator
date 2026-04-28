export interface EstimateRequest {
  query: string;
  save: boolean;
}

export interface ParsedTaxInput {
  tax_type: 'federal' | 'sales_use';
  filing_status?: string;
  gross_income?: number;
  deductions?: number;
  credits: number;
  purchase_amount?: number;
  state?: string;
  is_use_tax: boolean;
  confidence: number;
  missing_fields: string[];
}

export interface TaxEstimate {
  tax_type: 'federal' | 'sales_use';
  taxable_amount: number;
  estimated_tax: number;
  effective_rate: number;
  marginal_rate?: number;
  details: Record<string, unknown>;
}

export interface EstimateResponse {
  parsed_input: ParsedTaxInput;
  estimate: TaxEstimate;
  summary: string;
  disclaimer: string;
  saved: boolean;
  storage_status: 'skipped' | 'saved' | 'not_configured' | 'failed';
}

