import { TestBed } from '@angular/core/testing';

import { Answer, Evidence } from '../../core/api.models';
import { AnalysisResult, toLines } from './analysis-result';

const EVIDENCE: Evidence = {
  chunk_id: 'C4',
  file: 'app.log',
  start_line: 10,
  end_line: 12,
  score: 0.03,
  text: [
    '2026-03-14T09:00:00Z INFO orders ok',
    '2026-03-14T09:00:01Z ERROR orders pool exhausted',
    '2026-03-14T09:00:02Z WARN orders slow',
  ].join('\n'),
};

const ANSWER: Answer = {
  id: 'abc',
  status: 'answered',
  question: 'Why are orders failing?',
  model: 'ollama/qwen3:4b',
  notes: [],
  evidence: [EVIDENCE, { ...EVIDENCE, chunk_id: 'C9', start_line: 90, end_line: 92 }],
  hypotheses: [
    {
      cause: 'The DB connection pool is exhausted',
      explanation: 'Requests wait for connections.',
      confidence: 'high',
      next_steps: ['Raise the pool size'],
      citations: [{ chunk_id: 'C4', file: 'app.log', start_line: 10, end_line: 12 }],
    },
  ],
};

describe('toLines', () => {
  it('numbers lines from the chunk start and detects levels', () => {
    const lines = toLines(EVIDENCE, []);
    expect(lines.map((l) => l.number)).toEqual([10, 11, 12]);
    expect(lines.map((l) => l.level)).toEqual(['info', 'error', 'warn']);
    expect(lines.every((l) => !l.cited)).toBe(true);
  });

  it('marks lines inside a citation of the same chunk', () => {
    const cited = toLines(EVIDENCE, [
      { chunk_id: 'C4', file: 'app.log', start_line: 11, end_line: 11 },
    ]);
    expect(cited.map((l) => l.cited)).toEqual([false, true, false]);
    const otherChunk = toLines(EVIDENCE, [
      { chunk_id: 'C9', file: 'app.log', start_line: 11, end_line: 11 },
    ]);
    expect(otherChunk.some((l) => l.cited)).toBe(false);
  });
});

describe('AnalysisResult', () => {
  async function render(answer: Answer) {
    const fixture = TestBed.createComponent(AnalysisResult);
    fixture.componentRef.setInput('answer', answer);
    await fixture.whenStable();
    return fixture.nativeElement as HTMLElement;
  }

  it('renders the hypothesis, confidence and citation chip', async () => {
    const el = await render(ANSWER);
    expect(el.querySelector('.banner')?.getAttribute('data-status')).toBe('answered');
    expect(el.querySelector('.hypothesis h3')?.textContent).toContain('connection pool');
    expect(el.querySelector('.confidence')?.textContent).toContain('high');
    expect(el.querySelector('.cite')?.textContent).toContain('app.log:10–12');
  });

  it('expands cited evidence and collapses the rest', async () => {
    const el = await render(ANSWER);
    const chunks = el.querySelectorAll('.chunk');
    expect(chunks[0].querySelector('.log')).toBeTruthy();
    expect(chunks[1].querySelector('.log')).toBeNull();
  });

  it('explains insufficient evidence without hypotheses', async () => {
    const el = await render({ ...ANSWER, status: 'insufficient_evidence', hypotheses: [] });
    expect(el.querySelector('.banner')?.textContent).toContain('Nothing was guessed');
    expect(el.querySelector('.hypothesis')).toBeNull();
  });
});
