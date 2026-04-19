import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { Pill } from '../components/Pill';
import { StatusChip } from '../components/StatusChip';
import { TruthTag } from '../components/TruthTag';
import { PanelCard } from '../components/Subcard';

type Filter = 'all' | 'active' | 'blocked' | 'degraded' | 'done' | 'stalled';

export function RunsList() {
  const { adapter, version } = useData();
  const projects = useMemo(() => adapter.listProjects(), [adapter, version]);
  const [filter, setFilter] = useState<Filter>('all');
  const [q, setQ] = useState('');

  const allRuns = projects.flatMap(p =>
    p.workUnits.flatMap(w => w.runs.map(r => ({ r, p, w }))),
  );

  const filtered = allRuns.filter(({ r }) => {
    if (filter !== 'all' && r.status !== filter) return false;
    if (q && !(r.label.toLowerCase().includes(q.toLowerCase()) || r.id.includes(q))) return false;
    return true;
  });

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1200px] mx-auto px-6 py-6 space-y-4">
        <div className="flex items-end gap-3">
          <div>
            <div className="label-mono mb-1">RUNS</div>
            <div className="text-[22px] text-text font-medium tracking-tight">all runs · across projects</div>
          </div>
          <TruthTag kind="derived" />
          <div className="ml-auto font-mono text-[11px] text-muted">{filtered.length} / {allRuns.length}</div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {(['all', 'active', 'blocked', 'degraded', 'done', 'stalled'] as Filter[]).map(f => (
            <Pill key={f} active={filter === f} tone={filter === f ? 'accent' : 'default'} onClick={() => setFilter(f)}>
              {f}
            </Pill>
          ))}
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="filter by label or id…"
            className="ml-auto bg-panel border border-border rounded-sm px-2.5 py-1 font-mono text-[11px] text-text outline-none focus:border-border-strong w-64"
          />
        </div>

        <PanelCard title="RUN LIST">
          <div className="divide-y divide-border">
            {filtered.length === 0 && <div className="px-4 py-6 text-[12px] text-faint italic text-center">No runs match.</div>}
            {filtered.map(({ r, p, w }) => (
              <Link
                key={`${p.id}-${w.id}-${r.id}`}
                to={`/p/${p.id}/wu/${w.id}/r/${encodeURIComponent(r.id)}`}
                className="flex items-center gap-3 px-4 py-2.5 hover:bg-surface"
              >
                <span className="font-mono text-[10px] text-muted w-16">{r.id}</span>
                <span className="text-[12px] text-text flex-1 truncate">{r.label}</span>
                <span className="font-mono text-[10px] text-faint w-40 truncate">{p.label}/{w.id}</span>
                <span className="font-mono text-[10px] text-faint w-16">{r.ts}</span>
                <StatusChip status={r.status} />
              </Link>
            ))}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
