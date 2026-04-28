// src/app/app.component.ts
import { Component } from '@angular/core';
import { TaxWidgetComponent } from './components/tax-widget/tax-widget.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [TaxWidgetComponent],
  template: `<app-tax-widget></app-tax-widget>`,
})
export class AppComponent {}
