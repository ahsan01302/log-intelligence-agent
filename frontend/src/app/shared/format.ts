import { AnswerStatus } from '../core/api.models';

export const STATUS_LABEL: Record<AnswerStatus, string> = {
  answered: 'Answered',
  insufficient_evidence: 'Not enough evidence',
  degraded: 'Evidence only',
};

/** "just now", "5 min ago", "3 h ago", else a short date. */
export function timeAgo(iso: string, now = Date.now()): string {
  const then = new Date(iso).getTime();
  const s = Math.max(0, Math.round((now - then) / 1000));
  if (s < 45) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86_400) return `${Math.round(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}
