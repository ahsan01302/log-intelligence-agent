import { HttpEventType } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';

import { errorMessage, LogIntelApi } from './log-intel-api';
import { WorkspaceStore } from './workspace-store';

export interface UploadItem {
  id: number;
  name: string;
  size: number;
  state: 'queued' | 'uploading' | 'done' | 'error';
  progress: number;
  message: string;
}

// Same rules the backend enforces in service.py, checked here first for a clearer message.
const ALLOWED = ['.log', '.txt'];
const SAFE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/;

export function validateFile(file: { name: string; size: number }, maxMb: number): string | null {
  const dot = file.name.lastIndexOf('.');
  const suffix = dot >= 0 ? file.name.slice(dot).toLowerCase() : '';
  if (!ALLOWED.includes(suffix)) return 'Only .log and .txt files are accepted';
  if (!SAFE_NAME.test(file.name)) return "Rename it: use letters, digits, '.', '_' or '-' only";
  if (file.size === 0) return 'File is empty';
  if (file.size > maxMb * 1024 * 1024) return `File is larger than ${maxMb} MB`;
  return null;
}

/** Upload queue at app level, so uploads keep going (and stay visible) across pages. */
@Injectable({ providedIn: 'root' })
export class UploadStore {
  private readonly api = inject(LogIntelApi);
  private readonly workspace = inject(WorkspaceStore);

  /** Newest first. */
  readonly items = signal<UploadItem[]>([]);
  private readonly files = new Map<number, File>();
  private nextId = 1;
  private busy = false;

  add(files: File[], maxMb: number): void {
    const added = files.map((file): UploadItem => {
      const problem = validateFile(file, maxMb);
      const id = this.nextId++;
      if (!problem) this.files.set(id, file);
      return {
        id,
        name: file.name,
        size: file.size,
        state: problem ? 'error' : 'queued',
        progress: 0,
        message: problem ?? 'Waiting',
      };
    });
    this.items.update((list) => [...added.reverse(), ...list]);
    this.next();
  }

  clearFinished(): void {
    this.items.update((list) =>
      list.filter((i) => i.state === 'queued' || i.state === 'uploading'),
    );
  }

  /** One file at a time: each upload re-indexes everything on the server. */
  private next(): void {
    if (this.busy) return;
    const item = [...this.items()].reverse().find((i) => i.state === 'queued');
    const file = item && this.files.get(item.id);
    if (!item || !file) return;
    this.busy = true;
    this.patch(item.id, { state: 'uploading', message: 'Uploading' });

    this.api.upload(file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          const progress = Math.round((event.loaded / event.total) * 100);
          this.patch(item.id, { progress, message: progress < 100 ? 'Uploading' : 'Indexing' });
        } else if (event.type === HttpEventType.Response && event.body) {
          const r = event.body;
          this.patch(item.id, {
            state: 'done',
            progress: 100,
            message: `Indexed: ${r.chunks} chunks across ${r.files_indexed} file(s)`,
          });
          this.workspace.refresh();
        }
      },
      error: (err) => this.finish(item.id, { state: 'error', message: errorMessage(err) }),
      complete: () => this.finish(item.id, {}),
    });
  }

  private finish(id: number, patch: Partial<UploadItem>): void {
    this.patch(id, patch);
    this.files.delete(id);
    this.busy = false;
    this.next();
  }

  private patch(id: number, patch: Partial<UploadItem>): void {
    this.items.update((list) => list.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  }
}
