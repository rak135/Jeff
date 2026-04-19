import type { TruthClass } from '../lib/contracts/types';

const MAP: Record<TruthClass, { label: string; cls: string }> = {
  canonical: { label: 'CANONICAL', cls: 'text-canonical border-canonical/40' },
  support: { label: 'SUPPORT', cls: 'text-support border-support/40' },
  derived: { label: 'DERIVED', cls: 'text-derived border-derived/40' },
  memory: { label: 'MEMORY', cls: 'text-memory border-memory/40' },
  local: { label: 'UI-LOCAL', cls: 'text-faint border-faint/40' },
};

export function TruthTag({ kind }: { kind: TruthClass }) {
  const m = MAP[kind];
  return (
    <span
      className={`font-mono text-[9px] tracking-[.15em] px-1.5 py-[2px] rounded-sm border ${m.cls}`}
    >
      {m.label}
    </span>
  );
}

export function BackingTag({ backing }: { backing: 'real' | 'future' | 'mock' }) {
  const MAP2 = {
    real: 'text-approved border-approved/40',
    future: 'text-pending border-pending/40',
    mock: 'text-faint border-faint/40',
  } as const;
  return (
    <span className={`font-mono text-[9px] tracking-[.15em] px-1.5 py-[2px] rounded-sm border uppercase ${MAP2[backing]}`}>
      {backing === 'future' ? 'future · prototype' : backing}
    </span>
  );
}
