import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { InvestigationStore } from '../../core/investigation-store';
import { WorkspaceStore } from '../../core/workspace-store';
import { AnalysisResult } from '../../shared/analysis-result/analysis-result';
import { Icon } from '../../shared/icon';
import { UploadDropzone } from '../../shared/upload-dropzone/upload-dropzone';

@Component({
  selector: 'app-overview',
  imports: [FormsModule, AnalysisResult, Icon, UploadDropzone],
  templateUrl: './overview.html',
  styleUrl: './overview.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Overview {
  protected readonly store = inject(WorkspaceStore);
  protected readonly investigation = inject(InvestigationStore);

  protected readonly noLogs = computed(() => (this.store.health()?.chunks ?? 0) === 0);
  protected readonly canAnalyze = computed(
    () =>
      this.investigation.draft().trim().length >= 3 &&
      !this.investigation.analyzing() &&
      !this.noLogs(),
  );

  constructor() {
    this.investigation.setOverviewVisible(true);
    inject(DestroyRef).onDestroy(() => this.investigation.setOverviewVisible(false));
  }

  protected analyze(): void {
    if (this.canAnalyze()) this.investigation.run(this.investigation.draft().trim());
  }
}
