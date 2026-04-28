// src/app/models/tax.model.ts

export interface TaxResult {
  state: string;
  state_name: string;
  sale_amount: number;
  product_type: string;
  tax_type_label: string;
  rate_pct: number;
  tax_amount: number;
  total_due: number;
  has_nexus: boolean;
  nexus_reason: string;
  is_exempt: boolean;
  exemption_reason: string;
  notes: string[];
  summary: string;
  extracted: ExtractedFields;
}

export interface ExtractedFields {
  sale_amount: number | null;
  state: string | null;
  product_type: string;
  is_use_tax: boolean;
  business_type: string;
  notes: string;
}

export interface HistoryItem {
  query: string;
  state: string;
  tax_amount: number;
  rate_pct: number;
  at: string;
}
