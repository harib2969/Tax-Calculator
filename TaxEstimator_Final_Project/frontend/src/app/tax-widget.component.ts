import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { TaxApiService } from './tax-api.service';
import { EstimateResponse } from './tax.models';

@Component({
  selector: 'app-tax-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <main class="page-shell">
      <section class="widget" aria-label="Tax estimator widget">
        <div class="masthead">
          <p class="eyebrow">US Federal + Sales/Use Tax</p>
          <h1>Natural Language Tax Estimator</h1>
          <p class="subcopy">Ask a planning question and get a structured estimate with a GenAI-ready explanation.</p>
        </div>

        <form class="query-panel" (ngSubmit)="submit()">
          <label for="query">Tax question</label>
          <textarea
            id="query"
            name="query"
            [(ngModel)]="query"
            rows="5"
            placeholder="Estimate federal tax for single filer earning $120,000 with $5,000 credits."
          ></textarea>

          <div class="actions">
            <label class="toggle">
              <input type="checkbox" name="save" [(ngModel)]="saveResult">
              <span>Save estimate</span>
            </label>
            <button type="submit" [disabled]="loading || query.trim().length < 5">
              {{ loading ? 'Estimating...' : 'Estimate' }}
            </button>
          </div>
        </form>

        <div class="examples" aria-label="Example prompts">
          <button type="button" *ngFor="let example of examples" (click)="query = example">{{ example }}</button>
        </div>

        <p class="error" *ngIf="error">{{ error }}</p>

        <section class="results" *ngIf="result">
          <div class="metric">
            <span>Estimated tax</span>
            <strong>{{ result.estimate.estimated_tax | currency:'USD':'symbol':'1.0-2' }}</strong>
          </div>
          <div class="metric">
            <span>Taxable amount</span>
            <strong>{{ result.estimate.taxable_amount | currency:'USD':'symbol':'1.0-2' }}</strong>
          </div>
          <div class="metric">
            <span>Effective rate</span>
            <strong>{{ result.estimate.effective_rate | percent:'1.2-2' }}</strong>
          </div>

          <article class="summary">
            <h2>GenAI Summary</h2>
            <p>{{ result.summary }}</p>
          </article>

          <article class="assumptions">
            <h2>Assumptions Used</h2>
            <dl *ngIf="result.estimate.tax_type === 'federal'; else salesUseAssumptions">
              <div>
                <dt>Tax year</dt>
                <dd>{{ detailValue('tax_year') }}</dd>
              </div>
              <div>
                <dt>Filing status</dt>
                <dd>{{ formatText(detailValue('filing_status')) }}</dd>
              </div>
              <div>
                <dt>Deduction used</dt>
                <dd>{{ numberDetail('deduction_used') | currency:'USD':'symbol':'1.0-2' }}</dd>
              </div>
              <div>
                <dt>Credits used</dt>
                <dd>{{ numberDetail('credits_used') | currency:'USD':'symbol':'1.0-2' }}</dd>
              </div>
            </dl>

            <ng-template #salesUseAssumptions>
              <dl>
                <div>
                  <dt>State</dt>
                  <dd>{{ detailValue('state') }}</dd>
                </div>
                <div>
                  <dt>Rate used</dt>
                  <dd>{{ numberDetail('state_rate') | percent:'1.2-3' }}</dd>
                </div>
                <div>
                  <dt>Tax type</dt>
                  <dd>{{ result.parsed_input.is_use_tax ? 'Use tax' : 'Sales tax' }}</dd>
                </div>
                <div>
                  <dt>Rate note</dt>
                  <dd>{{ detailValue('rate_note') }}</dd>
                </div>
              </dl>
            </ng-template>
          </article>

          <p class="disclaimer">{{ result.disclaimer }}</p>
        </section>
      </section>
    </main>
  `
})
export class TaxWidgetComponent {
  query = 'Estimate federal tax for single filer earning $120,000 with $5,000 credits.';
  saveResult = true;
  loading = false;
  error = '';
  result: EstimateResponse | null = null;

  examples = [
    'Estimate federal tax for single filer earning $120,000 with $5,000 credits.',
    'I am married filing jointly, income is $210k, itemized deductions are $40k, credits $2,000.',
    'Sales tax for a $2,500 laptop shipped to California.',
    'Use tax estimate for $900 purchase in New York.'
  ];

  constructor(private readonly taxApi: TaxApiService) {}

  detailValue(key: string): string {
    const value = this.result?.estimate.details[key];
    return value === undefined || value === null || value === '' ? 'Not provided' : String(value);
  }

  numberDetail(key: string): number {
    const value = this.result?.estimate.details[key];
    return typeof value === 'number' ? value : 0;
  }

  formatText(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  submit(): void {
    this.error = '';
    this.result = null;
    this.loading = true;

    this.taxApi
      .estimate({ query: this.query, save: this.saveResult })
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (response) => (this.result = response),
        error: (err) => {
          this.error = err?.error?.detail ?? 'Unable to estimate tax. Check the backend is running on port 8000.';
        }
      });
  }
}
