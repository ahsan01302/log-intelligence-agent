import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { UploadDropzone } from '../shared/upload-dropzone/upload-dropzone';
import { UploadStore } from './upload-store';

const log = (name: string) => new File(['2026-01-01T00:00:00Z INFO a x\n'], name);
const DONE = { filename: 'a.log', files_indexed: 1, chunks: 3, embeddings: true };

describe('UploadStore', () => {
  let http: HttpTestingController;
  let store: UploadStore;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    store = TestBed.inject(UploadStore);
  });

  it('uploads one file at a time, in the order added', () => {
    store.add([log('a.log'), log('b.log')], 20);
    expect(store.items().map((i) => [i.name, i.state])).toEqual([
      ['b.log', 'queued'],
      ['a.log', 'uploading'],
    ]);
    http.expectOne('/api/upload').flush(DONE);
    expect(store.items().find((i) => i.name === 'a.log')?.state).toBe('done');
    expect(store.items().find((i) => i.name === 'b.log')?.state).toBe('uploading');
    http.expectOne('/api/upload').flush(DONE);
    expect(store.items().every((i) => i.state === 'done')).toBe(true);
  });

  it('rejects invalid files without sending them', () => {
    store.add([log('notes.pdf')], 20);
    expect(store.items()[0].state).toBe('error');
    http.expectNone('/api/upload');
  });

  it('keeps upload progress when the dropzone is destroyed and recreated', async () => {
    const first = TestBed.createComponent(UploadDropzone);
    await first.whenStable();
    store.add([log('a.log')], 20);
    first.destroy(); // user switches pages mid-upload

    const second = TestBed.createComponent(UploadDropzone);
    await second.whenStable();
    expect(second.nativeElement.textContent).toContain('a.log');
    http.expectOne('/api/upload').flush(DONE);
    await second.whenStable();
    expect(second.nativeElement.textContent).toContain('Indexed: 3 chunks');
  });
});
