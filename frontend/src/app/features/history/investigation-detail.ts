import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, effect, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Investigation } from '../../core/api.models';
import { errorMessage, LogIntelApi } from '../../core/log-intel-api';
import { AnalysisResult } from '../../shared/analysis-result/analysis-result';
import { STATUS_LABEL } from '../../shared/format';
import { Icon } from '../../shared/icon';

@Component({
  selector: 'app-investigation-detail',
  imports: [DatePipe, RouterLink, AnalysisResult, Icon],
  template: `
    <a routerLink="/history" class="back">← All investigations</a>
    @if (error()) {
      <div class="error" role="alert">
        <app-icon name="alert" />
        <span>{{ error() }}</span>
      </div>
    }
    @if (item(); as inv) {
      <header class="page-head">
        <div>
          <h1>{{ inv.question }}</h1>
          <p class="subtle">
            {{ inv.created_at | date: 'medium' }} · {{ inv.model ?? 'no model' }} ·
            <span class="pill" [attr.data-status]="inv.status">{{ statusLabel[inv.status] }}</span>
          </p>
        </div>
        <button type="button" class="btn-secondary danger" (click)="remove(inv.id)">
          <app-icon name="trash" [size]="16" /> Delete
        </button>
      </header>
      <app-analysis-result [answer]="inv.answer" />
    } @else if (!error()) {
      <p class="subtle">Loading…</p>
    }
  `,
  styles: `
    :host {
      display: grid;
      gap: 16px;
    }
    .back {
      color: var(--muted);
      font-size: var(--text-sm);
      text-decoration: none;
      &:hover {
        color: var(--text);
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvestigationDetail {
  private readonly api = inject(LogIntelApi);
  private readonly router = inject(Router);

  /** Bound from the :id route parameter (withComponentInputBinding). */
  readonly id = input.required<string>();

  protected readonly item = signal<Investigation | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly statusLabel = STATUS_LABEL;

  constructor() {
    effect(() => {
      const id = this.id();
      this.item.set(null);
      this.error.set(null);
      this.api.investigation(id).subscribe({
        next: (inv) => this.item.set(inv),
        error: (err) => this.error.set(errorMessage(err)),
      });
    });
  }

  protected remove(id: string): void {
    this.api.deleteInvestigation(id).subscribe({
      next: () => this.router.navigate(['/history']),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
