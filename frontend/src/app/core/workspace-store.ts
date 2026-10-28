import { computed, DestroyRef, inject, Injectable, signal } from '@angular/core';

import { Health } from './api.models';
import { LogIntelApi } from './log-intel-api';

export type ModelState = 'checking' | 'ready' | 'no-model' | 'offline';

const POLL_MS = 15_000;

/** Backend status shared by the top bar, status cards and settings page. */
@Injectable({ providedIn: 'root' })
export class WorkspaceStore {
  private readonly api = inject(LogIntelApi);

  readonly health = signal<Health | null>(null);
  readonly offline = signal(false);

  readonly modelState = computed<ModelState>(() => {
    if (this.offline()) return 'offline';
    const h = this.health();
    if (!h) return 'checking';
    return h.llm ? 'ready' : 'no-model';
  });

  /** "qwen3:4b" from "ollama/qwen3:4b". */
  readonly modelName = computed(() => this.health()?.llm?.split('/').slice(1).join('/') || null);

  constructor() {
    this.refresh();
    const timer = setInterval(() => this.refresh(), POLL_MS);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }

  refresh(): void {
    this.api.health().subscribe({
      next: (h) => {
        this.health.set(h);
        this.offline.set(false);
      },
      error: () => this.offline.set(true),
    });
  }
}
