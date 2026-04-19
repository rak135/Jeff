import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { LayerPanel } from '../components/LayerPanel';
import { Pill } from '../components/Pill';
import { StatusChip, Dot } from '../components/StatusChip';
import { TruthTag, BackingTag } from '../components/TruthTag';
import { PanelCard } from '../components/Subcard';

type Tab = 'lifecycle' | 'trace' | 'rationale' | 'telemetry' | 'related';

export function RunDetail() {
  const { projectId, workUnitId, runId } = useParams();
  const navigate = useNavigate();
  const { adapter, version, refresh } = useData();
  const project = useMemo(() => (projectId ? adapter.getProject(projectId) : undefined), [adapter, projectId, version]);
  const wu = project?.workUnits.find(w => w.id === workUnitId);
  const run = wu?.runs.find(r => r.id === decodeURIComponent(runId ?? ''));
  const [openLayer, setOpenLayer] = useState<string | null>('execution');
  const [tab, setTab] = useState<Tab>('lifecycle');
  const [approved, setApproved] = useState(false);

  if (!project || !wu || !run) {
    return (
      <div className="h-full flex items-center justify-center text-muted text-[13px]">
        Run not found.
        <Link to="/overview" className="ml-2 text-accent hover:underline">back to overview</Link>
      </div>
    );
  }

  const layers = run.layers;
  const changes = adapter.listChanges().filter(c => c.runId === run.id);

  return (
    <div className="h-full flex flex-col">
      {/* scope/header bar */}
      <div className="flex-shrink-0 px-5 py-3 border-b border-border bg-panel flex items-center gap-3 flex-wrap">
        <span className="label-mono">RUN</span>
        <span className="font-mono text-[13px] text-text">
          <span className="font-medium">{project.label}</span>
          <span className="mx-1.5 text-faint">/</span>
          <span className="text-accent font-medium">{wu.id}</span>
          <span className="mx-1.5 text-faint">/</span>
          <span className="font-medium">{run.id}</span>
        </span>
        <StatusChip status={run.status} />
        <span className="font-mono text-[10px] text-faint">{run.ts}</span>

        <div className="ml-auto flex gap-1.5">
          <Pill onClick={() => navigate(`/p/${project.id}/wu/${wu.id}`)}>history</Pill>
          <Pill onClick={() => { adapter.retryRun(project.id, wu.id, run.id); refresh(); }} tone="default">retry</Pill>
          <Pill onClick={() => { adapter.revalidateContext(project.id, wu.id, run.id); refresh(); }}>revalidate</Pill>
        </div>
      </div>

      {/* tab strip */}
      <div className="flex-shrink-0 px-5 border-b border-border bg-panel flex items-center gap-1">
        {(['lifecycle', 'trace', 'rationale', 'telemetry', 'related'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 font-mono text-[11px] uppercase tracking-widest border-b-2 -mb-px ${tab === t ? 'text-text border-accent' : 'text-muted border-transparent hover:text-text'}`}
          >
            {t}
          </button>
        ))}
        <div className="ml-auto font-mono text-[10px] text-faint py-2">
          {tab === 'lifecycle' && 'canonical ordering · 10 layers'}
          {tab === 'trace' && 'derived · reconstructed from telemetry'}
          {tab === 'rationale' && 'derived · model thought stream'}
          {tab === 'telemetry' && 'support · no truth claim'}
          {tab === 'related' && 'support · linked artifacts'}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-[1100px] mx-auto px-5 py-4">
          {/* operator message */}
          <div className="px-3.5 py-3 mb-2.5 bg-surface border border-border rounded-sm">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="label-mono">operator</span>
              <span className="ml-auto font-mono text-[10px] text-faint">{run.ts} · request</span>
            </div>
            <div className="text-[13px] text-text leading-relaxed">{run.operatorMsg}</div>
          </div>

          {/* banners — preserve honest distinctions */}
          {run.status === 'blocked' && (
            <BlockedBanner run={run} onAction={(kind: string) => {
              if (kind === 'revalidate') { adapter.revalidateContext(project.id, wu.id, run.id); refresh(); }
              if (kind === 'retry') { adapter.retryRun(project.id, wu.id, run.id); refresh(); }
            }} />
          )}

          {run.status === 'active' && run.governance?.decision === 'permitted' && !approved && (
            <ApprovalBanner run={run} onAck={() => setApproved(true)} />
          )}

          {run.status === 'degraded' && <DegradedBanner run={run} />}

          {tab === 'lifecycle' && (
            <>
              <LoopStrip layers={layers} />
              {layers.map(l => (
                <LayerPanel key={l.id} layer={l} runId={run.id} open={openLayer === l.id} onToggle={() => setOpenLayer(openLayer === l.id ? null : l.id)} />
              ))}
            </>
          )}

          {tab === 'trace' && <TraceTimeline layers={layers} />}
          {tab === 'rationale' && <RationaleView layers={layers} />}
          {tab === 'telemetry' && <TelemetryView run={run} />}
          {tab === 'related' && <RelatedView changes={changes} />}

          <div className="h-12" />
        </div>
      </div>

      {/* composer */}
      <div className="flex-shrink-0 border-t border-border bg-panel px-5 py-3">
        <Composer placeholder={run.status === 'blocked' ? 'Respond to escalation…' : `Continue within ${wu.label}…`} />
      </div>
    </div>
  );
}

function LoopStrip({ layers }: { layers: any[] }) {
  const c = {
    done: layers.filter(l => l.status === 'done').length,
    active: layers.filter(l => l.status === 'active').length,
    pending: layers.filter(l => l.status === 'pending').length,
    blocked: layers.filter(l => l.status === 'blocked').length,
    skipped: layers.filter(l => l.status === 'skipped').length,
  };
  return (
    <div className="px-3 py-2 bg-panel border border-border rounded-sm mb-2 flex items-center gap-3 flex-wrap">
      <span className="label-mono">LOOP · 10 LAYERS</span>
      <span className="font-mono text-[10px] text-faint">
        {c.done} done · {c.active} active · {c.pending} pending · {c.blocked} blocked · {c.skipped} skipped
      </span>
      <span className="ml-auto font-mono text-[10px] text-faint">click a layer to expand</span>
    </div>
  );
}

function BlockedBanner({ run, onAction }: any) {
  return (
    <div className="px-3.5 py-3 mb-2.5 border border-blocked rounded-sm bg-blocked/5">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="w-2 h-2 rounded-full bg-blocked" />
        <span className="font-mono text-[10px] text-blocked tracking-widest">HONEST ESCALATION</span>
        <span className="ml-auto font-mono text-[10px] text-faint">blocked ≠ failed · read-only OK</span>
      </div>
      <div className="text-[13px] text-text leading-relaxed mb-2">Run blocked by readiness failure. Two conditions prevent honest continuation:</div>
      <div className="font-mono text-[11px] leading-7">
        {(run.readiness?.failing ?? []).map((f: string) => (
          <div key={f}>
            <span className="text-blocked">✕</span> <b>{f}</b>
          </div>
        ))}
        <div>
          <span className="text-approved">✓</span> read-only inspection may continue
        </div>
      </div>
      <div className="flex gap-1.5 mt-3 flex-wrap">
        <Pill onClick={() => onAction('revalidate')}>revalidate context</Pill>
        <Pill>resolve contradiction</Pill>
        <Pill onClick={() => onAction('retry')}>retry after fix</Pill>
        <Pill>read-only continue</Pill>
        <Pill>escalate</Pill>
      </div>
    </div>
  );
}

function ApprovalBanner({ run, onAck }: any) {
  return (
    <div className="px-3.5 py-3 mb-2.5 border border-pending rounded-sm bg-pending/5">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="w-2 h-2 rounded-full bg-pending" />
        <span className="font-mono text-[10px] text-pending tracking-widest">GOVERNANCE · APPROVED</span>
        <span className="ml-auto font-mono text-[10px] text-faint">approved ≠ applied</span>
      </div>
      <div className="text-[13px] text-text leading-relaxed mb-2">
        {run.governance?.policy} · action will execute but transition only fires after evaluation.
      </div>
      <div className="flex gap-1.5 flex-wrap">
        <button onClick={onAck} className="bg-approved text-white border-none font-mono text-[11px] px-3 py-1.5 rounded-sm font-medium hover:opacity-90">
          acknowledge
        </button>
        <Pill>reject</Pill>
        <Pill>defer</Pill>
        <Pill>escalate</Pill>
      </div>
    </div>
  );
}

function DegradedBanner({ run }: any) {
  return (
    <div className="px-3.5 py-3 mb-2.5 border border-degraded rounded-sm bg-degraded/5">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="w-2 h-2 rounded-full bg-degraded" />
        <span className="font-mono text-[10px] text-degraded tracking-widest">DEGRADED · PARTIAL SUCCESS</span>
        <span className="ml-auto font-mono text-[10px] text-faint">evaluation ≠ execution</span>
      </div>
      <div className="text-[13px] text-text">Evaluation returned partial coverage. Transition was not fired.</div>
    </div>
  );
}

function TraceTimeline({ layers }: { layers: any[] }) {
  return (
    <div className="border border-border rounded-sm bg-panel">
      <div className="px-4 py-2.5 border-b border-border flex items-center gap-2">
        <span className="label-mono">TRACE · reconstructed timeline</span>
        <TruthTag kind="derived" />
      </div>
      <div className="p-4">
        {layers.map((l, i) => (
          <div key={l.id} className="flex items-start gap-3 pb-3 relative">
            <div className="flex flex-col items-center">
              <Dot status={l.status} />
              {i < layers.length - 1 && <div className="w-px flex-1 bg-border mt-1 min-h-6" />}
            </div>
            <div className="flex-1 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] tracking-widest uppercase text-text">{l.label}</span>
                <span className="font-mono text-[10px] text-faint">{l.dur}</span>
              </div>
              <div className="text-[12px] text-muted mt-0.5">{l.sum}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RationaleView({ layers }: { layers: any[] }) {
  return (
    <PanelCard title="RATIONALE · selection & governance" truth={<TruthTag kind="canonical" />}>
      <div className="p-4 space-y-3 text-[13px] text-text leading-relaxed">
        <p>The run was scoped under <span className="text-accent">mutate_canonical_spec</span>. Two proposals were generated; a third would have been ceremonial.</p>
        <p><b>Selection</b> chose <span className="text-accent">opt-02</span> (cross-check path) for the marginal cost of catching basis drift.</p>
        <p><b>Governance</b> granted execution permission conditional on operator acknowledgment of canonical mutation risk.</p>
        <div className="font-mono text-[10px] text-faint pt-2 border-t border-border">rationale is canonical per INTERFACE_OPERATOR_SPEC · transitions fire only after evaluation</div>
      </div>
    </PanelCard>
  );
}

function TelemetryView({ run }: { run: any }) {
  return (
    <PanelCard title="TELEMETRY · support signals" truth={<BackingTag backing="future" />}>
      <div className="p-4 grid grid-cols-3 gap-3">
        {[
          ['layer count', '10'],
          ['readiness', `${run.readiness?.pass}/${run.readiness?.total}`],
          ['tokens', '8,412'],
          ['tool calls', '3'],
          ['retries', '0'],
          ['wall clock', '5m 42s'],
        ].map(([k, v]) => (
          <div key={k} className="border border-border rounded-sm p-3 bg-surface">
            <div className="label-mono">{k}</div>
            <div className="font-mono text-[16px] text-text mt-1">{v}</div>
          </div>
        ))}
      </div>
    </PanelCard>
  );
}

function RelatedView({ changes }: { changes: any[] }) {
  return (
    <PanelCard title="RELATED · artifacts & change proposals" truth={<TruthTag kind="support" />}>
      <div className="divide-y divide-border">
        {changes.length === 0 && <div className="px-4 py-3 text-[12px] text-faint italic">No linked change proposals.</div>}
        {changes.map(c => (
          <Link key={c.id} to={`/changes/${c.id}`} className="block px-4 py-2.5 hover:bg-surface">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-muted w-16">{c.id}</span>
              <span className="text-[12px] text-text flex-1 truncate">{c.title}</span>
              <span className="font-mono text-[9px] uppercase tracking-widest text-pending border border-pending/40 px-1.5 py-[2px] rounded-sm">{c.status.replace('_', ' ')}</span>
            </div>
          </Link>
        ))}
      </div>
    </PanelCard>
  );
}

function Composer({ placeholder }: { placeholder: string }) {
  const [val, setVal] = useState('');
  return (
    <div className="max-w-[1100px] mx-auto">
      <div className="border border-border-strong rounded-md bg-surface px-3 py-2.5">
        <textarea
          value={val}
          onChange={e => setVal(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-transparent border-none outline-none text-text text-[13px] resize-none min-h-[46px] leading-relaxed"
        />
        <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-border">
          <Pill>＋ attach</Pill>
          <Pill>⌕ research</Pill>
          <Pill>⎇ plan</Pill>
          <div className="ml-auto flex items-center gap-2">
            <span className="font-mono text-[10px] text-faint">submit as <b className="text-muted">proposal request</b></span>
            <button
              disabled={!val.trim()}
              onClick={() => setVal('')}
              className={`font-mono text-[11px] px-3.5 py-1.5 rounded-sm font-medium ${val.trim() ? 'bg-accent text-[#1a1816] hover:opacity-90 cursor-pointer' : 'bg-border text-faint cursor-not-allowed'}`}
            >
              submit →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
