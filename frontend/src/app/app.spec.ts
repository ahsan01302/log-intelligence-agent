import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';
import { Health } from './core/api.models';
import { InvestigationStore } from './core/investigation-store';

const HEALTH: Health = {
  status: 'ok',
  files: 2,
  chunks: 40,
  embeddings: true,
  llm: 'ollama/qwen3:4b',
  provider: 'ollama',
  embed_model: 'nomic-embed-text',
  max_upload_mb: 20,
  default_top_k: 5,
};

describe('App shell', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  it('shows the three navigation items', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const labels = [...fixture.nativeElement.querySelectorAll('.rail-label')].map((a: Element) =>
      a.textContent?.trim(),
    );
    expect(labels).toEqual(['Overview', 'History', 'Settings']);
  });

  it('shows the local model once health loads', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/health').flush(HEALTH);
    await fixture.whenStable();
    const status = fixture.nativeElement.querySelector('.model') as HTMLElement;
    expect(status.textContent).toContain('qwen3:4b · local');
    expect(status.dataset['state']).toBe('ready');
  });

  it('badges Overview while an analysis runs on another page, then when its result is ready', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/health').flush(HEALTH);
    const investigation = TestBed.inject(InvestigationStore);
    investigation.run('Why is checkout failing?'); // Overview page is not on screen
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.badge')?.getAttribute('data-badge')).toBe('running');
    expect(el.querySelector('.topbar')?.textContent).toContain('Analyzing');

    http.expectOne('/api/ask').flush({
      id: 'x',
      status: 'answered',
      question: 'q',
      hypotheses: [],
      evidence: [],
      model: null,
      notes: [],
    });
    await fixture.whenStable();
    expect(el.querySelector('.badge')?.getAttribute('data-badge')).toBe('ready');
    expect(el.querySelector('.topbar')?.textContent).not.toContain('Analyzing');
  });

  it('says the API is offline when health fails', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/health').error(new ProgressEvent('error'), { status: 0 });
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('.model').textContent).toContain('API offline');
  });
});
