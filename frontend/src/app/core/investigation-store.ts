import { computed, inject, Injectable, signal } from '@angular/core';

import { Answer } from './api.models';
import { errorMessage, LogIntelApi } from './log-intel-api';
import { PreferencesStore } from './preferences';

export type InvestigationState = 'idle' | 'analyzing' | 'done' | 'error';

/** The current investigation. It lives at app level, not in the Overview page, so a
 * request keeps its progress, result and error while the user visits other pages. */
@Injectable({ providedIn: 'root' })
export class InvestigationStore {
  private readonly api = inject(LogIntelApi);
  private readonly prefs = inject(PreferencesStore);

  /** The text in the question box (kept across page visits too). */
  readonly draft = signal('');
  readonly state = signal<InvestigationState>('idle');
  readonly question = signal('');
  readonly answer = signal<Answer | null>(null);
  readonly error = signal<string | null>(null);
  readonly elapsed = signal(0);
  /** A result or error arrived while the user was on another page. */
  readonly unseen = signal(false);

  readonly analyzing = computed(() => this.state() === 'analyzing');

  private overviewVisible = false;
  private timer?: ReturnType<typeof setInterval>;

  run(question: string): void {
    if (this.analyzing()) return;
    const { topK, mode } = this.prefs.value();
    this.state.set('analyzing');
    this.question.set(question);
    this.error.set(null);
    this.elapsed.set(0);
    const started = Date.now();
    this.timer = setInterval(
      () => this.elapsed.set(Math.floor((Date.now() - started) / 1000)),
      1000,
    );

    this.api.ask({ question, mode, ...(topK ? { top_k: topK } : {}) }).subscribe({
      next: (answer) => {
        this.answer.set(answer);
        this.finish('done');
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.finish('error');
      },
    });
  }

  /** Called by the Overview page while it is on screen. */
  setOverviewVisible(visible: boolean): void {
    this.overviewVisible = visible;
    if (visible) this.unseen.set(false);
  }

  private finish(state: InvestigationState): void {
    clearInterval(this.timer);
    this.state.set(state);
    if (!this.overviewVisible) this.unseen.set(true);
  }
}
