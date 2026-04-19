import type { LayerStatus, RunStatus } from '../lib/contracts/types';

/**
 * Status presentation kept explicit to preserve Jeff's semantic distinctions.
 * We never collapse blocked/deferred/escalated/degraded/inconclusive/stalled into
 * a single "failed" blob.
 */
const GLYPH: Record<string, string> = {
  done: '✓',
  active: '●',
  pending: '○',
  blocked: '✕',
  degraded: '△',
  skipped: '—',
  deferred: '⏸',
  escalated: '▲',
  inconclusive: '?',
  stalled: '⋯',
};

const COLOR: Record<string, string> = {
  done: 'text-approved border-approved/40',
  active: 'text-accent border-accent/60',
  pending: 'text-faint border-faint/40',
  blocked: 'text-blocked border-blocked/50',
  degraded: 'text-degraded border-degraded/50',
  skipped: 'text-faint border-faint/30',
  deferred: 'text-muted border-muted/40',
  escalated: 'text-blocked border-blocked/60',
  inconclusive: 'text-degraded border-degraded/40',
  stalled: 'text-muted border-muted/40',
};

export function statusGlyph(s: LayerStatus | RunStatus) {
  return GLYPH[s] ?? '○';
}

export function statusColorClass(s: LayerStatus | RunStatus) {
  return COLOR[s] ?? 'text-faint border-faint/40';
}

export function StatusChip({ status }: { status: LayerStatus | RunStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1 font-mono text-[9px] tracking-[.15em] uppercase px-1.5 py-[2px] rounded-sm border ${statusColorClass(status)}`}
    >
      <span>{statusGlyph(status)}</span>
      <span>{status}</span>
    </span>
  );
}

export function Dot({ status }: { status: LayerStatus | RunStatus }) {
  const bg =
    status === 'active'
      ? 'bg-accent'
      : status === 'done'
      ? 'bg-approved'
      : status === 'blocked' || status === 'escalated'
      ? 'bg-blocked'
      : status === 'degraded' || status === 'inconclusive'
      ? 'bg-degraded'
      : status === 'pending'
      ? 'bg-pending'
      : 'bg-faint';
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${bg}`} />;
}
