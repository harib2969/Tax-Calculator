import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EstimateRequest, EstimateResponse } from './tax.models';

@Injectable({ providedIn: 'root' })
export class TaxApiService {
  private readonly apiUrl = 'http://localhost:8000/api/estimate';

  constructor(private readonly http: HttpClient) {}

  estimate(request: EstimateRequest): Observable<EstimateResponse> {
    return this.http.post<EstimateResponse>(this.apiUrl, request);
  }
}

