import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { TruthTag, BackingTag } from '../components/TruthTag';

export function Memory() {
  const { adapter, version } = useData();
  const mem = useMemo(() => adapter.listMemory(), [adapter, version]);

  const candidates = mem.filter(m => m.status === 'candidate');
  const committed = mem.filter(m => m.status === 'committed');

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1100px] mx-auto px-6 py-6 space-y-4">
        <div className="flex items-end gap-3">
          <div>
            <div className="label-mono mb-1">MEMORY</div>
            <div className="text-[22px] text-text font-medium tracking-tight">committed knowledge & candidates</div>
            <div className="text-[13px] text-muted mt-1">
              Memory is useful, evidence-linked knowledge. <b className="text-text">Memory ≠ canonical truth.</b>
              {' '}Canonical state may reference only committed memory IDs.
            </div>
          </div>
          <BackingTag backing="future" />
          <TruthTag kind="memory" />
        </div>

        <PanelCard title={`CANDIDATES · ${candidates.length}`} truth={<TruthTag kind="memory" />}>
          <div className="divide-y divide-border">
            {candidates.length === 0 && <div className="px-4 py-4 text-[12px] text-faint italic">No pending candidates.</div>}
            {candidates.map(m => (
              <div key={m.id} className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-memory">{m.id}</span>
                  <span className="text-[12px] text-text flex-1">{m.text}</span>
                  <span className="font-mono text-[9px] text-pending border border-pending/50 px-1.5 py-[2px] rounded-sm uppercase tracking-widest">pending</span>
                </div>
                <div className="font-mono text-[10px] text-faint mt-1">
                  from <Link className="text-accent hover:underline" to="#">{m.sourceRunId}</Link>
                  {m.evidenceLink ? ` · evidence · ${m.evidenceLink}` : ' · no evidence link'}
                </div>
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard title={`COMMITTED · ${committed.length}`} truth={<TruthTag kind="memory" />}>
          <div className="divide-y divide-border">
            {committed.map(m => (
              <div key={m.id} className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-memory">{m.id}</span>
                  <span className="text-[12px] text-text flex-1">{m.text}</span>
                  <span className="font-mono text-[9px] text-approved border border-approved/50 px-1.5 py-[2px] rounded-sm uppercase tracking-widest">committed</span>
                </div>
                <div className="font-mono text-[10px] text-faint mt-1">
                  from {m.sourceRunId} · evidence · {m.evidenceLink}
                </div>
              </div>
            ))}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
