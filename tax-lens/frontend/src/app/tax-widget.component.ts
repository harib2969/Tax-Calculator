import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';

import { ApiService } from './api.service';
import { SessionService } from './session.service';
import {
  CompanySummaryRow,
  TaxBreakdown,
  ChatMessage,
} from './tax.types';

@Component({
  selector: 'tax-widget',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    InputTextModule,
    CardModule,
    TagModule,
    DialogModule,
    ProgressSpinnerModule,
    TooltipModule,
  ],
  template: `
    <div class="tx-shell">
      <header class="tx-header">
        <div>
          <h1>Tax Lens</h1>
          <p class="muted">Natural-language tax advisory · 2024 tax year · Azure OpenAI agentic chat</p>
        </div>
        <div class="header-actions">
          <span *ngIf="loading()" class="status">Loading...</span>
          <span class="status badge">{{ companies().length }} companies loaded</span>
        </div>
      </header>

      <div class="tx-body">
        <!-- LEFT: Company grid + breakdown -->
        <section class="left-pane">
          <p-card>
            <ng-template pTemplate="title">
              <div class="card-title">
                <span>Company Portfolio</span>
                <span class="muted small">Click a row to view full 7-step tax breakdown</span>
              </div>
            </ng-template>
            <p-table
              [value]="companies()"
              [paginator]="true"
              [rows]="10"
              [rowsPerPageOptions]="[10, 20, 50]"
              [globalFilterFields]="['company','entity','state']"
              styleClass="p-datatable-sm p-datatable-striped"
              selectionMode="single"
              [(selection)]="selectedRow"
              (onRowSelect)="onSelectRow($event.data)"
              dataKey="company"
            >
              <ng-template pTemplate="caption">
                <div class="table-caption">
                  <input
                    pInputText
                    type="text"
                    [(ngModel)]="filterText"
                    (input)="applyFilter(dt, $event)"
                    placeholder="Filter companies..."
                    #dt
                  />
                  <p-button
                    label="Refresh"
                    icon="pi pi-refresh"
                    severity="secondary"
                    [text]="true"
                    (onClick)="loadCompanies()"
                  />
                </div>
              </ng-template>
              <ng-template pTemplate="header">
                <tr>
                  <th pSortableColumn="company">Company <p-sortIcon field="company" /></th>
                  <th pSortableColumn="entity">Entity</th>
                  <th pSortableColumn="state">State</th>
                  <th pSortableColumn="gross_income" class="num">Gross Income <p-sortIcon field="gross_income" /></th>
                  <th pSortableColumn="total_tax" class="num">Total Tax <p-sortIcon field="total_tax" /></th>
                  <th pSortableColumn="effective_rate" class="num">Eff. Rate</th>
                </tr>
              </ng-template>
              <ng-template pTemplate="body" let-row>
                <tr [pSelectableRow]="row">
                  <td><strong>{{ row.company }}</strong></td>
                  <td><p-tag [value]="row.entity" [severity]="entitySeverity(row.entity)" /></td>
                  <td>{{ row.state }}</td>
                  <td class="num">{{ row.gross_income | currency:'USD':'symbol':'1.0-0' }}</td>
                  <td class="num">{{ row.total_tax | currency:'USD':'symbol':'1.0-0' }}</td>
                  <td class="num">{{ row.effective_rate | number:'1.2-2' }}%</td>
                </tr>
              </ng-template>
              <ng-template pTemplate="emptymessage">
                <tr><td colspan="6" class="muted">No companies. Make sure the backend loaded the Excel file.</td></tr>
              </ng-template>
            </p-table>
          </p-card>

          <!-- Tax breakdown card -->
          <p-card *ngIf="breakdown() as b" styleClass="breakdown-card">
            <ng-template pTemplate="title">
              <div class="card-title">
                <span>{{ b.company }} — Tax Breakdown</span>
                <p-button
                  icon="pi pi-comments"
                  label="Explain in chat"
                  size="small"
                  (onClick)="askExplain(b.company)"
                />
              </div>
            </ng-template>

            <div class="metric-grid">
              <div class="metric"><span class="muted">Federal Tax</span><strong>{{ b.summary.federal_tax | currency:'USD':'symbol':'1.0-0' }}</strong></div>
              <div class="metric"><span class="muted">State Tax</span><strong>{{ b.summary.state_tax | currency:'USD':'symbol':'1.0-0' }}</strong></div>
              <div class="metric primary"><span class="muted">Total Tax</span><strong>{{ b.summary.total_tax | currency:'USD':'symbol':'1.0-0' }}</strong></div>
              <div class="metric"><span class="muted">Effective Rate</span><strong>{{ b.summary.effective_rate | number:'1.2-2' }}%</strong></div>
            </div>

            <h3>Step-by-Step</h3>
            <ol class="steps">
              <li *ngFor="let line of b.explanation">{{ line }}</li>
            </ol>
          </p-card>
        </section>

        <!-- RIGHT: Chat panel -->
        <section class="right-pane">
          <p-card styleClass="chat-card">
            <ng-template pTemplate="title">
              <div class="card-title">
                <span>Ask Tax Lens</span>
                <p-button
                  icon="pi pi-trash"
                  severity="secondary"
                  [text]="true"
                  size="small"
                  pTooltip="Reset chat"
                  (onClick)="resetChat()"
                />
              </div>
            </ng-template>

            <div class="chat-scroll" #chatScroll>
              <div *ngIf="session.messages().length === 0" class="chat-empty">
                <p><strong>Try asking:</strong></p>
                <ul>
                  <li (click)="quickAsk('What is the total tax for Pacific Manufacturing Co?')">What is the total tax for Pacific Manufacturing Co?</li>
                  <li (click)="quickAsk('Walk me through how you calculated Atlas Construction Group&apos;s federal tax.')">Walk me through Atlas Construction Group's federal tax</li>
                  <li (click)="quickAsk('What if Pine Grove Retail Inc moved to Texas?')">What if Pine Grove moved to Texas?</li>
                  <li (click)="quickAsk('Compare Pacific Manufacturing Co and Atlas Construction Group.')">Compare Pacific Manufacturing vs Atlas Construction</li>
                  <li (click)="quickAsk('Top 5 companies by effective tax rate.')">Top 5 by effective tax rate</li>
                  <li (click)="quickAsk('Which companies could save the most by restructuring?')">Which companies could save the most by restructuring?</li>
                </ul>
              </div>

              <div
                *ngFor="let m of session.messages()"
                class="chat-msg"
                [class.user]="m.role === 'user'"
                [class.assistant]="m.role === 'assistant'"
              >
                <div class="chat-bubble">
                  <div class="chat-content">{{ m.content }}</div>
                  <div *ngIf="m.toolCalls && m.toolCalls.length" class="tool-chips">
                    <span class="chip" *ngFor="let t of m.toolCalls">
                      <i class="pi pi-bolt"></i> {{ t }}
                    </span>
                  </div>
                </div>
              </div>

              <div *ngIf="session.isThinking()" class="chat-msg assistant">
                <div class="chat-bubble thinking">
                  <p-progressSpinner styleClass="tiny-spinner" strokeWidth="3" />
                  <span>Thinking…</span>
                </div>
              </div>
            </div>

            <div class="chat-input">
              <input
                pInputText
                [(ngModel)]="userInput"
                (keydown.enter)="send()"
                placeholder="Ask about a company, run a what-if, compare, or explain a rule..."
                [disabled]="session.isThinking()"
              />
              <p-button
                icon="pi pi-send"
                label="Send"
                (onClick)="send()"
                [disabled]="session.isThinking() || !userInput.trim()"
              />
            </div>
          </p-card>
        </section>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; background: #f4f6fa; color: #1f2937; }
    .tx-shell { display: flex; flex-direction: column; height: 100%; }
    .tx-header {
      padding: 14px 24px; background: linear-gradient(120deg, #1d4ed8, #6366f1);
      color: #fff; display: flex; justify-content: space-between; align-items: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .tx-header h1 { margin: 0; font-size: 22px; letter-spacing: 0.3px; }
    .tx-header .muted { color: rgba(255,255,255,0.85); font-size: 12px; margin: 2px 0 0; }
    .header-actions { display: flex; gap: 8px; align-items: center; }
    .status { font-size: 12px; padding: 4px 10px; border-radius: 12px; background: rgba(255,255,255,0.18); }
    .status.badge { font-weight: 600; }

    .tx-body {
      display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px;
      padding: 16px; flex: 1; overflow: hidden;
    }
    @media (max-width: 1024px) { .tx-body { grid-template-columns: 1fr; } }
    .left-pane, .right-pane {
      display: flex; flex-direction: column; gap: 16px;
      overflow-y: auto; padding-right: 4px;
    }
    .right-pane { overflow: hidden; }

    .card-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .muted { color: #6b7280; }
    .small { font-size: 12px; font-weight: 400; }
    .num { text-align: right; }

    .table-caption { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .table-caption input { width: 320px; max-width: 100%; }

    .metric-grid {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 8px;
    }
    .metric {
      background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
      padding: 10px 12px; display: flex; flex-direction: column; gap: 4px;
    }
    .metric.primary { background: #eef2ff; border-color: #c7d2fe; }
    .metric strong { font-size: 18px; }
    .steps { padding-left: 18px; line-height: 1.7; font-size: 14px; }
    .steps li { margin-bottom: 4px; font-family: 'JetBrains Mono', 'Consolas', monospace; }

    /* Chat panel */
    :host ::ng-deep .chat-card { display: flex; flex-direction: column; height: 100%; }
    :host ::ng-deep .chat-card .p-card-body { flex: 1; display: flex; flex-direction: column; min-height: 0; }
    :host ::ng-deep .chat-card .p-card-content { flex: 1; display: flex; flex-direction: column; min-height: 0; }
    .chat-scroll {
      flex: 1; overflow-y: auto; padding: 8px 4px;
      display: flex; flex-direction: column; gap: 10px; min-height: 320px;
    }
    .chat-empty { color: #6b7280; font-size: 14px; }
    .chat-empty ul { padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
    .chat-empty li {
      cursor: pointer; padding: 8px 12px; border: 1px dashed #d1d5db; border-radius: 8px;
      transition: background 0.15s;
    }
    .chat-empty li:hover { background: #eef2ff; border-color: #6366f1; }

    .chat-msg { display: flex; }
    .chat-msg.user { justify-content: flex-end; }
    .chat-msg.assistant { justify-content: flex-start; }
    .chat-bubble {
      max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 14px;
      line-height: 1.5; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      white-space: pre-wrap; word-break: break-word;
    }
    .chat-msg.user .chat-bubble { background: #1d4ed8; color: white; border-bottom-right-radius: 2px; }
    .chat-msg.assistant .chat-bubble { background: #ffffff; border: 1px solid #e5e7eb; border-bottom-left-radius: 2px; }
    .chat-bubble.thinking { display: flex; align-items: center; gap: 8px; color: #6b7280; }
    :host ::ng-deep .tiny-spinner .p-progress-spinner-circle { stroke: #6366f1 !important; }
    :host ::ng-deep .tiny-spinner { width: 18px; height: 18px; }

    .tool-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
    .chip {
      font-size: 11px; padding: 2px 8px; border-radius: 10px;
      background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;
    }

    .chat-input {
      display: flex; gap: 8px; margin-top: 8px;
      padding-top: 8px; border-top: 1px solid #e5e7eb;
    }
    .chat-input input { flex: 1; }
  `],
})
export class TaxWidgetComponent implements OnInit {
  private api = inject(ApiService);
  session = inject(SessionService);

  companies = signal<CompanySummaryRow[]>([]);
  breakdown = signal<TaxBreakdown | null>(null);
  loading = signal(false);
  selectedRow: CompanySummaryRow | null = null;
  userInput = '';
  filterText = '';

  ngOnInit() {
    this.loadCompanies();
  }

  loadCompanies() {
    this.loading.set(true);
    this.api.listCompanies().subscribe({
      next: (res) => {
        this.companies.set(res.companies || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  onSelectRow(row: CompanySummaryRow) {
    if (!row) return;
    this.session.selectedCompany.set(row.company);
    this.api.getCompanyTax(row.company).subscribe((b) => this.breakdown.set(b));
  }

  applyFilter(table: any, evt: any) {
    table.value = (this.companies() || []).filter((r) =>
      `${r.company} ${r.entity} ${r.state}`
        .toLowerCase()
        .includes((this.filterText || '').toLowerCase())
    );
  }

  entitySeverity(entity: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
    switch (entity) {
      case 'C-Corp': return 'info';
      case 'S-Corp': return 'success';
      case 'LLC': return 'warning';
      case 'Partnership': return 'secondary';
      default: return 'secondary';
    }
  }

  askExplain(company: string) {
    this.quickAsk(`Walk me step-by-step through how ${company}'s tax was calculated.`);
  }

  quickAsk(text: string) {
    this.userInput = text;
    this.send();
  }

  send() {
    const text = (this.userInput || '').trim();
    if (!text || this.session.isThinking()) return;
    this.userInput = '';

    const userMsg: ChatMessage = { role: 'user', content: text, ts: Date.now() };
    this.session.addMessage(userMsg);
    this.session.isThinking.set(true);

    this.api.chat(this.session.sessionId, text).subscribe({
      next: (res) => {
        this.session.addMessage({
          role: 'assistant',
          content: res.reply,
          toolCalls: res.tool_calls_made,
          ts: Date.now(),
        });
        this.session.isThinking.set(false);
        setTimeout(() => this.scrollChatToBottom(), 30);
      },
      error: (err) => {
        this.session.addMessage({
          role: 'assistant',
          content:
            'Error reaching the backend. Make sure FastAPI is running on http://localhost:8000 and Azure OpenAI credentials are set in backend/.env.\n\nDetails: ' +
            (err?.message || 'unknown'),
          ts: Date.now(),
        });
        this.session.isThinking.set(false);
      },
    });
  }

  resetChat() {
    this.api.resetSession(this.session.sessionId).subscribe();
    this.session.reset();
  }

  private scrollChatToBottom() {
    const el = document.querySelector('.chat-scroll');
    if (el) el.scrollTop = el.scrollHeight;
  }
}
