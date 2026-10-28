import { Routes } from '@angular/router';

import { Overview } from './features/overview/overview';

export const routes: Routes = [
  { path: '', component: Overview, title: 'New investigation · Log Intelligence Agent' },
  {
    path: 'history',
    loadComponent: () => import('./features/history/history').then((m) => m.History),
    title: 'History · Log Intelligence Agent',
  },
  {
    path: 'history/:id',
    loadComponent: () =>
      import('./features/history/investigation-detail').then((m) => m.InvestigationDetail),
    title: 'Investigation · Log Intelligence Agent',
  },
  {
    path: 'settings',
    loadComponent: () => import('./features/settings/settings').then((m) => m.Settings),
    title: 'Settings · Log Intelligence Agent',
  },
  { path: '**', redirectTo: '' },
];
