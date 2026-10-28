import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { InvestigationStore } from './core/investigation-store';
import { WorkspaceStore } from './core/workspace-store';
import { Icon, IconName } from './shared/icon';

interface NavItem {
  path: string;
  label: string;
  icon: IconName;
  exact: boolean;
}

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly store = inject(WorkspaceStore);
  protected readonly investigation = inject(InvestigationStore);

  /** Badge on the Overview item, so a running or finished analysis is visible from any page. */
  protected readonly overviewBadge = computed(() => {
    if (this.investigation.analyzing()) return 'running';
    return this.investigation.unseen() ? 'ready' : null;
  });

  protected readonly nav: NavItem[] = [
    { path: '/', label: 'Overview', icon: 'overview', exact: true },
    { path: '/history', label: 'History', icon: 'history', exact: false },
    { path: '/settings', label: 'Settings', icon: 'settings', exact: false },
  ];

  protected readonly modelLabel = computed(() => {
    switch (this.store.modelState()) {
      case 'ready':
        return `${this.store.modelName()} · local`;
      case 'no-model':
        return 'No model: evidence only';
      case 'offline':
        return 'API offline';
      default:
        return 'Checking…';
    }
  });
}
