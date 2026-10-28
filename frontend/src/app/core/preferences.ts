import { effect, Injectable, signal } from '@angular/core';

import { RetrievalMode } from './api.models';

export interface Preferences {
  /** null means "use the server default". */
  topK: number | null;
  mode: RetrievalMode;
}

const KEY = 'log-intel.preferences';
const DEFAULTS: Preferences = { topK: null, mode: 'hybrid' };

/** Per-browser preferences sent with each question. Storage can be unavailable (private
 * windows, blocked site data), so every access is guarded and defaults always work. */
@Injectable({ providedIn: 'root' })
export class PreferencesStore {
  readonly value = signal<Preferences>(load());

  constructor() {
    effect(() => {
      try {
        localStorage.setItem(KEY, JSON.stringify(this.value()));
      } catch {
        // Not persisted; the in-memory value still applies for this session.
      }
    });
  }

  update(patch: Partial<Preferences>): void {
    this.value.update((current) => ({ ...current, ...patch }));
  }

  reset(): void {
    this.value.set({ ...DEFAULTS });
  }
}

function load(): Preferences {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? 'null');
    const topK = Number.isInteger(raw?.topK) && raw.topK >= 1 && raw.topK <= 20 ? raw.topK : null;
    const mode = ['hybrid', 'bm25', 'embed'].includes(raw?.mode) ? raw.mode : DEFAULTS.mode;
    return { topK, mode };
  } catch {
    return { ...DEFAULTS };
  }
}
