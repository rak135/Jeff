import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { TruthTag } from '../components/TruthTag';
import { StatusChip } from '../components/StatusChip';

export function Lookup() {
  const { adapter, version } = useData();
  const [q, setQ] = useState('');

  const runs = useMemo(() => {
    return adapter
      .listProjects()
      .flatMap(p => p.workUnits.flatMap(w => w.runs.map(r => ({ r, p, w }))));
  }, [adapter, version]);

  const changes = useMemo(() => adapter.listChanges(), [adapter, version]);
  const memory = useMemo(() => adapter.listMemory(), [adapter, version]);

  const qq = q.toLowerCase();
  const runHits = qq ? runs.filter(x => x.r.id.includes(q) || x.r.label.toLowerCase().includes(qq) || x.r.operatorMsg.toLowerCase().includes(qq)) : [];
  const changeHits = qq ? changes.filter(c => c.id.includes(q) || c.title.toLowerCase().includes(qq)) : [];
  const memHits = qq ? memory.filter(m => m.id.includes(q) || m.text.toLowerCase().includes(qq)) : [];

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1100px] mx-auto px-6 py-6 space-y-4">
        <div>
          <div className="label-mono mb-1">LOOKUP · HISTORY</div>
          <div className="text-[22px] text-text font-medium tracking-tight">search runs, changes, memory</div>
          <div className="text-[13px] text-muted mt-1">
            History is a <b className="text-text">support</b> artifact — it supports understanding, but it is not current truth.
          </div>
        </div>

        <input
          autoFocus
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="search run id, label, prompt, memory…"
          className="w-full bg-panel border border-border-strong rounded-sm px-3 py-2 font-mono text-[13px] text-text outline-none focus:border-accent"
        />

        {q && (
          <div className="space-y-3">
            <PanelCard title={`RUNS · ${runHits.length}`} truth={<TruthTag kind="support" />}>
              <div className="divide-y divide-border">
                {runHits.length === 0 && <div className="px-4 py-3 text-[12px] text-faint italic">No matching runs.</div>}
                {runHits.map(({ r, p, w }) => (
                  <Link key={`${p.id}-${w.id}-${r.id}`} to={`/p/${p.id}/wu/${w.id}/r/${encodeURIComponent(r.id)}`} className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-surface">
                    <span className="font-mono text-[10px] text-muted w-16">{r.id}</span>
                    <span className="text-[12px] text-text flex-1 truncate">{r.label}</span>
                    <span className="font-mono text-[10px] text-faint w-40 truncate">{p.label}/{w.id}</span>
                    <StatusChip status={r.status} />
                  </Link>
                ))}
              </div>
            </PanelCard>

            <PanelCard title={`CHANGES · ${changeHits.length}`} truth={<TruthTag kind="support" />}>
              <div className="divide-y divide-border">
                {changeHits.length === 0 && <div className="px-4 py-3 text-[12px] text-faint italic">No matching changes.</div>}
                {changeHits.map(c => (
                  <Link key={c.id} to={`/changes/${c.id}`} className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-surface">
                    <span className="font-mono text-[10px] text-muted w-14">{c.id}</span>
                    <span className="text-[12px] text-text flex-1 truncate">{c.title}</span>
                    <span className="font-mono text-[10px] text-faint">{c.status}</span>
                  </Link>
                ))}
              </div>
            </PanelCard>

            <PanelCard title={`MEMORY · ${memHits.length}`} truth={<TruthTag kind="memory" />}>
              <div className="divide-y divide-border">
                {memHits.length === 0 && <div className="px-4 py-3 text-[12px] text-faint italic">No matching memory.</div>}
                {memHits.map(m => (
                  <div key={m.id} className="flex items-center gap-2.5 px-4 py-2.5">
                    <span className="font-mono text-[10px] text-memory">{m.id}</span>
                    <span className="text-[12px] text-text flex-1">{m.text}</span>
                    <span className="font-mono text-[10px] text-faint">{m.status}</span>
                  </div>
                ))}
              </div>
            </PanelCard>
          </div>
        )}

        {!q && (
          <div className="text-[12px] text-faint italic text-center py-10">
            Type a query — lookup indexes runs, change proposals, and memory commits.
          </div>
        )}
      </div>
    </div>
  );
}
