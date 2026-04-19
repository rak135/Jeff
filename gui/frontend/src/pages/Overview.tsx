import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { TruthTag, BackingTag } from '../components/TruthTag';
import { StatusChip, Dot } from '../components/StatusChip';

export function Overview() {
  const { adapter, version } = useData();
  const projects = useMemo(() => adapter.listProjects(), [adapter, version]);
  const changes = useMemo(() => adapter.listChanges(), [adapter, version]);
  const health = useMemo(() => adapter.listHealth(), [adapter, version]);

  const allRuns = projects.flatMap(p => p.workUnits.flatMap(w => w.runs.map(r => ({ r, p, w }))));
  const counts = {
    active: allRuns.filter(x => x.r.status === 'active').length,
    blocked: allRuns.filter(x => x.r.status === 'blocked').length,
    degraded: allRuns.filter(x => x.r.status === 'degraded').length,
    stalled: allRuns.filter(x => x.r.status === 'stalled').length,
    done: allRuns.filter(x => x.r.status === 'done').length,
  };
  const attention = allRuns.filter(x => ['blocked', 'escalated', 'stalled', 'degraded'].includes(x.r.status));
  const pendingChanges = changes.filter(c => c.status === 'awaiting_approval');

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1200px] mx-auto px-6 py-6 space-y-5">
        <div>
          <div className="label-mono mb-1">OVERVIEW</div>
          <div className="text-[22px] text-text font-medium tracking-tight">operator console</div>
          <div className="text-[13px] text-muted mt-1">
            Present truth is the current state of projects, work units, and runs. History is not truth.
          </div>
        </div>

        {/* counts strip */}
        <div className="grid grid-cols-5 gap-2">
          {[
            { k: 'active', label: 'active', n: counts.active, tone: 'text-accent' },
            { k: 'blocked', label: 'blocked', n: counts.blocked, tone: 'text-blocked' },
            { k: 'degraded', label: 'degraded', n: counts.degraded, tone: 'text-degraded' },
            { k: 'stalled', label: 'stalled', n: counts.stalled, tone: 'text-muted' },
            { k: 'done', label: 'done', n: counts.done, tone: 'text-approved' },
          ].map(c => (
            <div key={c.k} className="border border-border bg-panel rounded-sm p-3">
              <div className="label-mono">{c.label}</div>
              <div className={`font-mono text-[28px] mt-1 ${c.tone}`}>{c.n}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <PanelCard
            title="ATTENTION · runs needing operator"
            truth={<TruthTag kind="derived" />}
            right={<span className="font-mono text-[10px] text-faint">{attention.length}</span>}
          >
            {attention.length === 0 ? (
              <div className="p-4 text-[12px] text-faint italic">Nothing needs you right now.</div>
            ) : (
              <div className="divide-y divide-border">
                {attention.map(({ r, p, w }) => (
                  <Link
                    key={`${p.id}-${w.id}-${r.id}`}
                    to={`/p/${p.id}/wu/${w.id}/r/${encodeURIComponent(r.id)}`}
                    className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-surface"
                  >
                    <Dot status={r.status} />
                    <span className="font-mono text-[10px] text-muted w-16">{r.id}</span>
                    <span className="text-[12px] text-text flex-1 truncate">{r.label}</span>
                    <span className="font-mono text-[10px] text-faint truncate max-w-[130px]">{p.label}/{w.id}</span>
                    <StatusChip status={r.status} />
                  </Link>
                ))}
              </div>
            )}
          </PanelCard>

          <PanelCard
            title="CHANGE PROPOSALS · awaiting approval"
            truth={<BackingTag backing="future" />}
            right={<Link to="/changes" className="font-mono text-[10px] text-muted hover:text-text">all →</Link>}
          >
            {pendingChanges.length === 0 ? (
              <div className="p-4 text-[12px] text-faint italic">No pending changes.</div>
            ) : (
              <div className="divide-y divide-border">
                {pendingChanges.map(c => (
                  <Link key={c.id} to={`/changes/${c.id}`} className="block px-4 py-2.5 hover:bg-surface">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-muted w-14">{c.id}</span>
                      <span className="text-[12px] text-text flex-1 truncate">{c.title}</span>
                      <span className="font-mono text-[9px] text-pending border border-pending/40 px-1.5 py-[2px] rounded-sm uppercase tracking-widest">
                        {c.status.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="font-mono text-[10px] text-faint mt-1">
                      {c.kind} · {c.projectId}/{c.workUnitId} · {c.createdAt}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </PanelCard>

          <PanelCard
            title="HEALTH · signals"
            truth={<BackingTag backing="future" />}
            right={<Link to="/health" className="font-mono text-[10px] text-muted hover:text-text">all →</Link>}
            className="col-span-2"
          >
            <div className="divide-y divide-border">
              {health.slice(0, 5).map(h => (
                <div key={h.id} className="flex items-center gap-2.5 px-4 py-2.5">
                  <Dot status={h.severity === 'ok' ? 'done' : h.severity} />
                  <span className="text-[12px] text-text flex-1">{h.name}</span>
                  <span className="font-mono text-[10px] text-faint">{h.scope}</span>
                  <span className="font-mono text-[10px] text-muted max-w-[320px] truncate">{h.detail}</span>
                </div>
              ))}
            </div>
          </PanelCard>
        </div>

        <div className="font-mono text-[10px] text-faint text-center pt-2">
          surfaces backed by <span className="text-approved">real</span> orchestrator data vs{' '}
          <span className="text-pending">future</span> simulated data are labeled throughout.
        </div>
      </div>
    </div>
  );
}
