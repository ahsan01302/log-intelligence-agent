import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Answer, Health } from '../../core/api.models';
import { Overview } from './overview';

const HEALTH: Health = {
  status: 'ok',
  files: 1,
  chunks: 4,
  embeddings: true,
  llm: 'ollama/qwen3:4b',
  provider: 'ollama',
  embed_model: 'nomic-embed-text',
  max_upload_mb: 20,
  default_top_k: 5,
};

const ANSWER: Answer = {
  id: 'h1',
  status: 'answered',
  question: 'Why are checkouts failing?',
  model: 'ollama/qwen3:4b',
  notes: [],
  evidence: [],
  hypotheses: [
    {
      cause: 'The TLS client certificate expired',
      explanation: '',
      confidence: 'high',
      next_steps: [],
      citations: [{ chunk_id: 'C3', file: 'tls.log', start_line: 3, end_line: 15 }],
    },
  ],
};

describe('Overview: leaving the page during an analysis', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Overview],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  async function open() {
    const fixture = TestBed.createComponent(Overview);
    await fixture.whenStable();
    http.match('/api/health').forEach((r) => r.flush(HEALTH));
    await fixture.whenStable();
    return fixture;
  }

  function text(fixture: { nativeElement: HTMLElement }): string {
    return fixture.nativeElement.textContent ?? '';
  }

  it('keeps showing progress after navigating away and back, then shows the answer', async () => {
    const first = await open();
    const input = first.nativeElement.querySelector('#question') as HTMLInputElement;
    input.value = 'Why are checkouts failing?';
    input.dispatchEvent(new Event('input'));
    await first.whenStable();
    (first.nativeElement.querySelector('form') as HTMLFormElement).dispatchEvent(
      new Event('submit'),
    );
    await first.whenStable();
    const ask = http.expectOne('/api/ask');
    expect(text(first)).toContain('Analyzing');

    first.destroy(); // user switches to History

    const second = await open(); // ...and comes back
    expect(text(second)).toContain('Analyzing');
    expect((second.nativeElement.querySelector('#question') as HTMLInputElement).value).toBe(
      'Why are checkouts failing?',
    );

    ask.flush(ANSWER); // the request finished while they were away
    await second.whenStable();
    expect(text(second)).toContain('The TLS client certificate expired');
    expect(text(second)).not.toContain('Analyzing');
  });

  it('keeps an error that happened while the user was away', async () => {
    const first = await open();
    const input = first.nativeElement.querySelector('#question') as HTMLInputElement;
    input.value = 'Why is it down?';
    input.dispatchEvent(new Event('input'));
    await first.whenStable();
    (first.nativeElement.querySelector('form') as HTMLFormElement).dispatchEvent(
      new Event('submit'),
    );
    await first.whenStable();
    const ask = http.expectOne('/api/ask');
    first.destroy();

    ask.flush({ detail: 'no logs indexed yet' }, { status: 409, statusText: 'Conflict' });
    const second = await open();
    expect(text(second)).toContain('no logs indexed yet');
  });
});
