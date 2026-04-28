// src/app/components/tax-widget/tax-widget.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TaxService } from '../../services/tax.service';
import { TaxResult, HistoryItem } from '../../models/tax.model';

@Component({
  selector: 'app-tax-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tax-widget.component.html',
  styleUrls: ['./tax-widget.component.scss'],
})
export class TaxWidgetComponent implements OnInit {
  query = '';
  loading = false;
  result: TaxResult | null = null;
  errorMsg = '';
  history: HistoryItem[] = [];

  examples = [
    'I earn $85,000 salary, single filer, $6,000 IRA contribution',
    'Married filing jointly, $140,000 combined income, $18,000 mortgage interest',
    'Freelancer, $90,000 net self-employment income, no deductions',
    'Head of household, $72,000 salary, 2 kids, $10,000 student loan interest',
  ];

  constructor(private taxService: TaxService) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  fillExample(ex: string): void {
    this.query = ex;
  }

  async analyze(): Promise<void> {
    if (!this.query.trim() || this.loading) return;
    this.loading = true;
    this.result = null;
    this.errorMsg = '';

    this.taxService.analyze(this.query).subscribe({
      next: (res) => {
        if (res['error']) {
          this.errorMsg = res['message'];
        } else {
          this.result = res as TaxResult;
        }
        this.loading = false;
        this.loadHistory();
      },
      error: (err) => {
        this.errorMsg = err?.error?.detail || 'Something went wrong. Is the backend running?';
        this.loading = false;
      },
    });
  }

  loadHistory(): void {
    this.taxService.getHistory().subscribe({
      next: (h) => (this.history = h),
      error: () => {},
    });
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.analyze();
    }
  }

  get summaryHtml(): string {
    if (!this.result?.summary) return '';
    return this.result.summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }
}
