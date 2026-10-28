import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { HistoryItem } from '../../core/api.models';
import { errorMessage, LogIntelApi } from '../../core/log-intel-api';
import { STATUS_LABEL, timeAgo } from '../../shared/format';
import { Icon } from '../../shared/icon';

@Component({
  selector: 'app-history',
  imports: [RouterLink, Icon],
  templateUrl: './history.html',
  styleUrl: './history.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class History {
  private readonly api = inject(LogIntelApi);

  protected readonly items = signal<HistoryItem[] | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly statusLabel = STATUS_LABEL;
  protected readonly timeAgo = timeAgo;

  constructor() {
    this.load();
  }

  protected load(): void {
    this.error.set(null);
    this.api.history().subscribe({
      next: (items) => this.items.set(items),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected remove(item: HistoryItem): void {
    this.api.deleteInvestigation(item.id).subscribe({
      next: () => this.items.update((list) => list?.filter((i) => i.id !== item.id) ?? null),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
