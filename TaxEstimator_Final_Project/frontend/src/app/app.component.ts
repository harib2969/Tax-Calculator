import { Component } from '@angular/core';
import { TaxWidgetComponent } from './tax-widget.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [TaxWidgetComponent],
  template: '<app-tax-widget />'
})
export class AppComponent {}

