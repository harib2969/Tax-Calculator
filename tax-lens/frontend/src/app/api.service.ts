import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Company,
  CompanySummaryRow,
  TaxBreakdown,
  ChatResponse,
} from './tax.types';

const BASE = '/api'; // proxied to http://localhost:8000 via proxy.conf.json

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  listCompanies(): Observable<{ count: number; companies: CompanySummaryRow[] }> {
    return this.http.get<{ count: number; companies: CompanySummaryRow[] }>(
      `${BASE}/companies`
    );
  }

  getCompany(name: string): Observable<Company> {
    return this.http.get<Company>(`${BASE}/companies/${encodeURIComponent(name)}`);
  }

  getCompanyTax(name: string): Observable<TaxBreakdown> {
    return this.http.get<TaxBreakdown>(
      `${BASE}/companies/${encodeURIComponent(name)}/tax`
    );
  }

  whatIf(companyName: string, overrides: Record<string, any>): Observable<any> {
    return this.http.post(`${BASE}/tax/whatif`, {
      company_name: companyName,
      overrides,
    });
  }

  compare(companyNames: string[]): Observable<any> {
    return this.http.post(`${BASE}/tax/compare`, { company_names: companyNames });
  }

  portfolio(): Observable<any> {
    return this.http.get(`${BASE}/tax/portfolio`);
  }

  chat(sessionId: string, message: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${BASE}/chat`, {
      session_id: sessionId,
      message,
    });
  }

  resetSession(sessionId: string): Observable<any> {
    return this.http.delete(`${BASE}/sessions/${encodeURIComponent(sessionId)}`);
  }
}
