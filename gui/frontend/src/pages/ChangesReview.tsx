import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { TruthTag, BackingTag } from '../components/TruthTag';
import { Pill } from '../components/Pill';

export function ChangesList() {
  const { adapter, version } = useData();
  const changes = useMemo(() => adapter.listChanges(), [adapter, version]);
  const [tab, setTab] = useState<'awaiting_approval' | 'approved' | 'applied' | 'rejected' | 'all'>('awaiting_approval');

  const filtered = tab === 'all' ? changes : changes.filter(c => c.status === tab);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1200px] mx-auto px-6 py-6 space-y-4">
        <div className="flex items-end gap-3">
          <div>
            <div className="label-mono mb-1">CHANGES · REVIEW</div>
            <div className="text-[22px] text-text font-medium tracking-tight">change proposals</div>
            <div className="text-[13px] text-muted mt-1">
              Each change is <b className="text-text">proposed</b> by a run and <b className="text-text">applied</b> only via transition.
              Approval is not application.
            </div>
          </div>
          <BackingTag backing="future" />
        </div>

        <div className="flex items-center gap-1.5">
          {(['awaiting_approval', 'approved', 'applied', 'rejected', 'all'] as const).map(t => (
            <Pill key={t} active={tab === t} tone={tab === t ? 'accent' : 'default'} onClick={() => setTab(t)}>
              {t.replace('_', ' ')}
            </Pill>
          ))}
        </div>

        <PanelCard title="PROPOSALS">
          <div className="divide-y divide-border">
            {filtered.length === 0 && <div className="px-4 py-6 text-[12px] text-faint italic text-center">No changes in this bucket.</div>}
            {filtered.map(c => (
              <Link key={c.id} to={`/changes/${c.id}`} className="block px-4 py-3 hover:bg-surface">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted w-14">{c.id}</span>
                  <span className="text-[13px] text-text flex-1 truncate">{c.title}</span>
                  <span className="font-mono text-[9px] text-muted border border-border px-1.5 py-[2px] rounded-sm uppercase tracking-widest">{c.kind}</span>
                  <StatusTag status={c.status} />
                </div>
                <div className="font-mono text-[10px] text-faint mt-1">
                  {c.projectId} / {c.workUnitId} / {c.runId} · {c.createdAt}
                </div>
              </Link>
            ))}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

export function ChangeDetail() {
  const { changeId } = useParams();
  const { adapter, version, refresh } = useData();
  const changes = useMemo(() => adapter.listChanges(), [adapter, version]);
  const change = changes.find(c => c.id === changeId);
  const navigate = useNavigate();

  if (!change) {
    return (
      <div className="h-full flex items-center justify-center text-muted text-[13px]">
        Change not found.
        <Link to="/changes" className="ml-2 text-accent hover:underline">back</Link>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1100px] mx-auto px-6 py-6 space-y-4">
        <div className="flex items-center gap-3">
          <Link to="/changes" className="font-mono text-[11px] text-muted hover:text-text">← all changes</Link>
          <span className="font-mono text-[10px] text-faint">·</span>
          <span className="font-mono text-[11px] text-accent">{change.id}</span>
          <BackingTag backing={change.backing} />
          <StatusTag status={change.status} />
        </div>

        <div>
          <div className="label-mono mb-1">{change.kind.replace('_', ' ')}</div>
          <div className="text-[22px] text-text font-medium tracking-tight">{change.title}</div>
          <div className="font-mono text-[11px] text-muted mt-1">
            proposed by <Link className="text-accent hover:underline" to={`/p/${change.projectId}/wu/${change.workUnitId}/r/${encodeURIComponent(change.runId)}`}>{change.runId}</Link>
            {' '}· {change.projectId} / {change.workUnitId} · {change.createdAt}
          </div>
        </div>

        {change.status === 'awaiting_approval' && (
          <div className="flex gap-2 border border-pending rounded-sm p-3 bg-pending/5">
            <div className="flex-1 text-[12px] text-text">
              <div className="font-mono text-[10px] text-pending tracking-widest mb-1">APPROVE ≠ APPLY</div>
              Approval unlocks execution. Canonical mutation happens only if evaluation supports the transition.
            </div>
            <button
              onClick={() => { adapter.approveChange(change.id); refresh(); }}
              className="bg-approved text-white font-mono text-[11px] px-3.5 py-1.5 rounded-sm hover:opacity-90"
            >
              approve
            </button>
            <Pill tone="blocked" onClick={() => { adapter.rejectChange(change.id); refresh(); }}>reject</Pill>
            <Pill>request changes</Pill>
            <Pill>defer</Pill>
          </div>
        )}

        {change.status === 'approved' && (
          <div className="border border-approved rounded-sm p-3 bg-approved/5 text-[12px] text-text">
            <div className="font-mono text-[10px] text-approved tracking-widest mb-1">APPROVED · AWAITING APPLY</div>
            Execution has permission. Canonical state updates on transition.
          </div>
        )}

        <PanelCard title="DIFF" truth={<TruthTag kind="support" />}>
          <div className="divide-y divide-border">
            {change.diff.map((d, i) => (
              <div key={i} className="p-4 space-y-2">
                <div className="font-mono text-[11px] text-muted">{d.path}</div>
                {d.before !== undefined && (
                  <pre className="font-mono text-[11px] leading-6 bg-blocked/5 text-blocked border border-blocked/30 rounded-sm p-2 whitespace-pre-wrap">- {d.before}</pre>
                )}
                {d.after !== undefined && (
                  <pre className="font-mono text-[11px] leading-6 bg-approved/5 text-approved border border-approved/30 rounded-sm p-2 whitespace-pre-wrap">+ {d.after}</pre>
                )}
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard title="IMPACT · derived" truth={<TruthTag kind="derived" />}>
          <div className="p-4 grid grid-cols-3 gap-3 font-mono text-[11px]">
            <Metric label="files touched" v={String(change.diff.length)} />
            <Metric label="truth class" v={change.kind.replace('_', ' ')} />
            <Metric label="reversibility" v={change.status === 'applied' ? 'via transition rollback' : 'n/a until applied'} />
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

function Metric({ label, v }: { label: string; v: string }) {
  return (
    <div className="border border-border rounded-sm p-2.5 bg-surface">
      <div className="label-mono">{label}</div>
      <div className="text-text text-[14px] mt-1">{v}</div>
    </div>
  );
}

function StatusTag({ status }: { status: string }) {
  const map: Record<string, string> = {
    awaiting_approval: 'text-pending border-pending/50',
    approved: 'text-approved border-approved/50',
    applied: 'text-approved border-approved/50 bg-approved/10',
    rejected: 'text-blocked border-blocked/50',
    draft: 'text-muted border-muted/50',
    withdrawn: 'text-faint border-faint/50',
  };
  return (
    <span className={`font-mono text-[9px] uppercase tracking-widest px-1.5 py-[2px] rounded-sm border ${map[status] ?? ''}`}>
      {status.replace('_', ' ')}
    </span>
  );
}
