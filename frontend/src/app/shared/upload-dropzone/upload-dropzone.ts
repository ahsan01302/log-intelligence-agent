import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';

import { UploadStore } from '../../core/upload-store';
import { Icon } from '../icon';

/** Drop target and progress list. The queue itself lives in UploadStore. */
@Component({
  selector: 'app-upload-dropzone',
  imports: [Icon],
  templateUrl: './upload-dropzone.html',
  styleUrl: './upload-dropzone.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadDropzone {
  protected readonly uploads = inject(UploadStore);

  readonly maxMb = input(20);

  protected readonly dragging = signal(false);
  protected readonly hasFinished = computed(() =>
    this.uploads.items().some((i) => i.state === 'done' || i.state === 'error'),
  );

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(true);
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    this.uploads.add(Array.from(event.dataTransfer?.files ?? []), this.maxMb());
  }

  protected onPick(input: HTMLInputElement): void {
    this.uploads.add(Array.from(input.files ?? []), this.maxMb());
    input.value = ''; // allow picking the same file again
  }

  protected formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}
