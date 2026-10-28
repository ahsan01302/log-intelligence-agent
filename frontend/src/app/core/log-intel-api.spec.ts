import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { errorMessage, LogIntelApi } from './log-intel-api';

describe('LogIntelApi', () => {
  let api: LogIntelApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(LogIntelApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts questions as a JSON body, never in the URL', () => {
    api.ask({ question: 'why?', top_k: 8, mode: 'bm25' }).subscribe();
    const req = http.expectOne('/api/ask');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ question: 'why?', top_k: 8, mode: 'bm25' });
    req.flush({});
  });

  it('uploads a file as multipart form data with progress events', () => {
    const file = new File(['2026-01-01T00:00:00Z INFO a x'], 'app.log');
    api.upload(file).subscribe();
    const req = http.expectOne('/api/upload');
    expect(req.request.body instanceof FormData).toBe(true);
    expect((req.request.body as FormData).get('file')).toBeTruthy();
    expect(req.request.reportProgress).toBe(true);
    req.flush({});
  });

  it('lists, fetches and deletes history', () => {
    api.history(10).subscribe();
    http.expectOne('/api/history?limit=10').flush([]);
    api.investigation('a/b').subscribe();
    http.expectOne('/api/history/a%2Fb').flush({});
    api.deleteInvestigation('abc').subscribe();
    expect(http.expectOne('/api/history/abc').request.method).toBe('DELETE');
  });
});

describe('errorMessage', () => {
  it('uses FastAPI detail strings and validation messages', () => {
    expect(errorMessage(new HttpErrorResponse({ status: 413, error: { detail: 'too big' } }))).toBe(
      'too big',
    );
    const validation = { detail: [{ msg: 'String should have at least 3 characters' }] };
    expect(errorMessage(new HttpErrorResponse({ status: 422, error: validation }))).toBe(
      'String should have at least 3 characters',
    );
  });

  it('explains a network failure', () => {
    expect(errorMessage(new HttpErrorResponse({ status: 0 }))).toContain('Cannot reach the API');
  });
});
