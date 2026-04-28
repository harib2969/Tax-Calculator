// src/app/services/tax.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TaxResult, HistoryItem } from '../models/tax.model';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class TaxService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  analyze(query: string): Observable<TaxResult | any> {
    return this.http.post(`${this.base}/api/analyze`, { query });
  }

  getHistory(limit = 8): Observable<HistoryItem[]> {
    return this.http.get<HistoryItem[]>(`${this.base}/api/history?limit=${limit}`);
  }
}
