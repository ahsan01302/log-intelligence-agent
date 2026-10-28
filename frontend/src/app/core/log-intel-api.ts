import { HttpClient, HttpErrorResponse, HttpEvent } from '@angular/common/http';
import { inject, Injectable, InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';

import {
  Answer,
  AskRequest,
  Health,
  HistoryItem,
  Investigation,
  UploadResponse,
} from './api.models';

/** Base path of the API. The dev server and nginx both proxy /api to the FastAPI backend. */
export const API_BASE = new InjectionToken<string>('API_BASE', { factory: () => '/api' });

@Injectable({ providedIn: 'root' })
export class LogIntelApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE);

  health(): Observable<Health> {
    return this.http.get<Health>(`${this.base}/health`);
  }

  /** Emits upload progress events, then the response. */
  upload(file: File): Observable<HttpEvent<UploadResponse>> {
    const body = new FormData();
    body.append('file', file, file.name);
    return this.http.post<UploadResponse>(`${this.base}/upload`, body, {
      observe: 'events',
      reportProgress: true,
    });
  }

  ask(request: AskRequest): Observable<Answer> {
    return this.http.post<Answer>(`${this.base}/ask`, request);
  }

  history(limit = 50): Observable<HistoryItem[]> {
    return this.http.get<HistoryItem[]>(`${this.base}/history`, { params: { limit } });
  }

  investigation(id: string): Observable<Investigation> {
    return this.http.get<Investigation>(`${this.base}/history/${encodeURIComponent(id)}`);
  }

  deleteInvestigation(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/history/${encodeURIComponent(id)}`);
  }
}

/** Turns an HTTP failure into one readable sentence, using FastAPI's `detail` when present. */
export function errorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) {
      return 'Cannot reach the API. Is the backend running on port 8000?';
    }
    const detail = error.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail[0]?.msg) {
      return detail[0].msg;
    }
    return `Request failed (${error.status} ${error.statusText})`;
  }
  return error instanceof Error ? error.message : 'Something went wrong';
}
