import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { RetrievalMode } from '../../core/api.models';
import { PreferencesStore } from '../../core/preferences';
import { WorkspaceStore } from '../../core/workspace-store';

@Component({
  selector: 'app-settings',
  imports: [],
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Settings {
  protected readonly store = inject(WorkspaceStore);
  protected readonly prefs = inject(PreferencesStore);

  protected readonly modes: { value: RetrievalMode; label: string; hint: string }[] = [
    { value: 'hybrid', label: 'Hybrid', hint: 'Keywords + embeddings, fused. Best default.' },
    { value: 'bm25', label: 'Keyword (BM25)', hint: 'Exact tokens like error codes and ids.' },
    {
      value: 'embed',
      label: 'Embeddings',
      hint: 'Meaning-based; falls back to keyword if unavailable.',
    },
  ];

  protected setTopK(value: string): void {
    const n = Number(value);
    this.prefs.update({ topK: value === '' ? null : Math.min(20, Math.max(1, Math.round(n))) });
  }
}
