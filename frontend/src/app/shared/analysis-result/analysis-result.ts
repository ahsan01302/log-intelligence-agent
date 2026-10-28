import {
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  signal,
} from '@angular/core';

import { Answer, Citation, Evidence } from '../../core/api.models';
import { Icon } from '../icon';

export interface LogLine {
  number: number;
  text: string;
  level: 'error' | 'warn' | 'info' | 'debug' | null;
  cited: boolean;
}

const LEVEL = /\b(FATAL|CRITICAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\b/;

/** Splits an evidence chunk into numbered lines, marking the ones a hypothesis cites. */
export function toLines(evidence: Evidence, cited: Citation[]): LogLine[] {
  const ranges = cited.filter((c) => c.chunk_id === evidence.chunk_id && c.file === evidence.file);
  return evidence.text.split('\n').map((text, i) => {
    const number = evidence.start_line + i;
    const match = LEVEL.exec(text)?.[1];
    const level = !match
      ? null
      : /FATAL|CRITICAL|ERROR/.test(match)
        ? 'error'
        : match.startsWith('WARN')
          ? 'warn'
          : match === 'INFO'
            ? 'info'
            : 'debug';
    const isCited = ranges.some((r) => number >= r.start_line && number <= r.end_line);
    return { number, text, level, cited: isCited };
  });
}

@Component({
  selector: 'app-analysis-result',
  imports: [Icon],
  templateUrl: './analysis-result.html',
  styleUrl: './analysis-result.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AnalysisResult {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly answer = input.required<Answer>();

  /** Chunk ids the user expanded; cited chunks start expanded. */
  private readonly toggled = signal<Set<string>>(new Set());
  protected readonly highlighted = signal<string | null>(null);

  protected readonly citations = computed(() =>
    this.answer().hypotheses.flatMap((h) => h.citations),
  );

  protected readonly citedIds = computed(() => new Set(this.citations().map((c) => c.chunk_id)));

  protected readonly evidence = computed(() =>
    this.answer().evidence.map((e) => ({
      ...e,
      cited: this.citedIds().has(e.chunk_id),
      lines: toLines(e, this.citations()),
    })),
  );

  protected isOpen(chunkId: string): boolean {
    return this.citedIds().has(chunkId) !== this.toggled().has(chunkId);
  }

  protected toggle(chunkId: string): void {
    this.toggled.update((set) => {
      const next = new Set(set);
      if (!next.delete(chunkId)) next.add(chunkId);
      return next;
    });
  }

  protected jumpTo(citation: Citation): void {
    if (!this.isOpen(citation.chunk_id)) this.toggle(citation.chunk_id);
    this.highlighted.set(citation.chunk_id);
    // Wait a frame so a just-expanded chunk is rendered before scrolling.
    requestAnimationFrame(() => {
      this.host.nativeElement
        .querySelector(`#evidence-${citation.chunk_id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    setTimeout(() => this.highlighted.set(null), 1600);
  }
}
