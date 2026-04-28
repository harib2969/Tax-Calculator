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
    'I sold $12,000 of SaaS to a customer in Texas',
    'Sold $5,500 physical goods to a buyer in California, have a warehouse there',
    'Bought $8,000 of equipment from an Oregon vendor, I\'m based in New York — do I owe use tax?',
    'I sell groceries online, $3,200 to customers in Florida',
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
