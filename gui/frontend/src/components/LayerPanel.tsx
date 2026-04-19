import { Fragment, useState } from 'react';
import type { LayerFrame } from '../lib/contracts/types';
import { statusGlyph, statusColorClass } from './StatusChip';
import { Subcard } from './Subcard';
import { TruthTag } from './TruthTag';
import { Pill } from './Pill';

interface Props {
  layer: LayerFrame;
  runId: string;
  open: boolean;
  onToggle: () => void;
}

const INPUT_ROWS: Record<string, Array<[string, string, any?]>> = {
  context: [['scope', 'jeff / … / {rid}'], ['trigger', 'operator request'], ['state read', 'fresh snapshot', 'canonical']],
  research: [['scope', 'jeff / … / {rid}'], ['question', '"memory vs canonical state"'], ['context', 'context bundle', 'support'], ['policy', 'internet_research · auto']],
  proposal: [['scope', 'jeff / … / {rid}'], ['context', 'context + research', 'support'], ['constraint', 'mutate_canonical_spec']],
  selection: [['scope', 'jeff / … / {rid}'], ['options', 'opt-01, opt-02', 'support'], ['direction', 'truth-first', 'canonical']],
  governance: [['scope', 'jeff / … / {rid}'], ['selection', 'opt-02', 'canonical'], ['policy', 'mutate_canonical_spec']],
  execution: [['scope', 'jeff / … / {rid}'], ['action', 'draft §Memory', 'canonical'], ['permit', 'approved + ready', 'canonical']],
  outcome: [['scope', 'jeff / … / {rid}'], ['expects', 'execution result']],
  evaluation: [['scope', 'jeff / … / {rid}'], ['goal', 'draft matches canonical spec'], ['outcome', 'pending']],
  memory: [['scope', 'jeff / … / {rid}'], ['source', 'evaluation verdict · pending']],
  transition: [['scope', 'jeff / … / {rid}'], ['intent', 'apply §Memory'], ['basis', 'evaluation + memory']],
};

const REASONING: Record<string, Array<{ kind: string; text: string }>> = {
  context: [
    { kind: 'note', text: 'reading state snapshot…' },
    { kind: 'ok', text: 'snapshot fresh' },
    { kind: 'note', text: 'retrieving committed memory' },
    { kind: 'ok', text: '2 refs loaded' },
  ],
  research: [
    { kind: 'note', text: 'searching: memory vs state' },
    { kind: 'ok', text: '4 candidates' },
    { kind: 'think', text: 'blog source is secondary — illustrative only' },
    { kind: 'ok', text: '3 internal sources aligned' },
  ],
  proposal: [
    { kind: 'note', text: 'generating candidates…' },
    { kind: 'think', text: 'direct-draft is fine — no contradictions' },
    { kind: 'think', text: 'cross-check is cheap insurance' },
    { kind: 'ok', text: '2 honest options · 3rd would be ceremonial' },
  ],
  selection: [
    { kind: 'think', text: 'comparing against truth-first direction' },
    { kind: 'think', text: 'opt-02 catches drift for marginal cost' },
    { kind: 'ok', text: 'opt-02 · honest choice' },
    { kind: 'note', text: 'selection ≠ execution permission' },
  ],
  governance: [
    { kind: 'note', text: 'invoking mutate_canonical_spec' },
    { kind: 'ok', text: 'operator approval · explicit' },
    { kind: 'ok', text: 'readiness 4/4 pass' },
    { kind: 'think', text: 'approved ≠ applied' },
  ],
  execution: [
    { kind: 'note', text: 'opening artifact' },
    { kind: 'stream', text: '## Memory' },
    { kind: 'stream', text: 'Memory stores useful, committed knowledge.' },
    { kind: 'think', text: 'keep memory≠truth explicit' },
    { kind: 'stream', text: 'Canonical state may reference only committed memory IDs.' },
  ],
  outcome: [
    { kind: 'note', text: 'waiting for execution' },
    { kind: 'note', text: 'will normalize artifacts + logs' },
  ],
  evaluation: [
    { kind: 'note', text: 'will compare outcome to goal' },
    { kind: 'note', text: 'verdicts: success / degraded / partial / inconclusive' },
  ],
  memory: [
    { kind: 'note', text: 'only accept candidates with evidence link' },
    { kind: 'think', text: 'memory ≠ truth' },
  ],
  transition: [
    { kind: 'note', text: 'transitions = only truth mutation path' },
    { kind: 'think', text: 'will not fire unless evaluation supports it' },
  ],
};

function ReasoningGlyph({ k }: { k: string }) {
  const g = k === 'ok' ? '✓' : k === 'warn' ? '!' : k === 'think' ? '›' : k === 'stream' ? '▌' : '·';
  const c =
    k === 'ok'
      ? 'text-approved'
      : k === 'warn'
      ? 'text-pending'
      : k === 'think'
      ? 'text-memory'
      : k === 'stream'
      ? 'text-text'
      : 'text-muted';
  return <span className={`w-3 inline-block text-center ${c}`}>{g}</span>;
}

function LayerInput({ layerId, runId }: { layerId: string; runId: string }) {
  const [mode, setMode] = useState<'summary' | 'raw'>('summary');
  const rows = (INPUT_ROWS[layerId] ?? []).map(([k, v, tag]) => [k, v.replace('{rid}', runId), tag]) as Array<[string, string, any?]>;
  return (
    <Subcard
      label="INPUT · context given to model"
      kindTag={<TruthTag kind="derived" />}
      right={
        <div className="flex gap-1">
          <Pill onClick={() => setMode('summary')} active={mode === 'summary'} tone="default">summary</Pill>
          <Pill onClick={() => setMode('raw')} active={mode === 'raw'} tone="default">raw</Pill>
        </div>
      }
    >
      {mode === 'summary' ? (
        <div className="px-3 py-2.5 grid grid-cols-[110px_1fr] gap-x-2.5 gap-y-1 font-mono text-[11px]">
          {rows.map(([k, v, tag], i) => (
            <Fragment key={i}>
              <div className="text-faint">{k}</div>
              <div className="text-text flex gap-1.5 items-center flex-wrap">
                {v}
                {tag && <TruthTag kind={tag} />}
              </div>
            </Fragment>
          ))}
        </div>
      ) : (
        <pre className="px-3 py-2.5 font-mono text-[11px] leading-6 text-text bg-surface whitespace-pre-wrap overflow-auto max-h-64">
{`{
  "layer": "${layerId}",
  "scope": {"project":"jeff","work_unit":"...", "run":"${runId}"},
  "inputs": ${JSON.stringify(Object.fromEntries(rows.map(r => [r[0], r[1]])), null, 2)}
}`}
        </pre>
      )}
    </Subcard>
  );
}

function LayerReasoning({ layerId }: { layerId: string }) {
  const stream = REASONING[layerId] ?? [];
  return (
    <Subcard label="REASONING · model thought stream" kindTag={<TruthTag kind="derived" />}>
      <div className="px-3 py-2.5 bg-surface font-mono text-[11px] leading-7 max-h-60 overflow-auto">
        {stream.map((s, i) => (
          <div key={i} className="flex gap-2">
            <ReasoningGlyph k={s.kind} />
            <div
              className={`flex-1 ${s.kind === 'stream' ? 'text-text pl-1.5 border-l-2 border-accent/30 bg-accent/5' : s.kind === 'think' ? 'text-memory italic' : 'text-muted'}`}
            >
              {s.text}
            </div>
          </div>
        ))}
      </div>
    </Subcard>
  );
}

function LayerOutput({ layer }: { layer: LayerFrame }) {
  const id = layer.id;
  let body: any;
  if (id === 'research') {
    const rows: Array<[string, string, string, any]> = [
      ['01', 'Memory design in agentic systems', 'blog.example.org/memory', 'derived'],
      ['02', 'State vs memory separation (paper)', 'arxiv.org/abs/2401.xxxxx', 'derived'],
      ['03', 'MEMORY_SPEC.md §1–4', 'internal', 'canonical'],
      ['04', 'mem#0093 contradiction log', 'internal', 'memory'],
    ];
    body = (
      <div className="divide-y divide-border">
        {rows.map(([n, title, src, kind]) => (
          <div key={n} className="flex items-center gap-2.5 px-3 py-2">
            <span className="font-mono text-[10px] text-faint w-5">{n}</span>
            <div className="flex-1">
              <div className="text-[12px] text-text">{title}</div>
              <div className="font-mono text-[10px] text-muted">{src}</div>
            </div>
            <TruthTag kind={kind} />
          </div>
        ))}
      </div>
    );
  } else if (id === 'proposal') {
    const opts = [
      { id: 'opt-01', sel: false, label: 'direct draft from committed memory spec', risk: 'low', cost: '18s' },
      { id: 'opt-02', sel: true, label: 'draft + cross-check contradictions log', risk: 'low', cost: '32s' },
    ];
    body = (
      <div className="p-3 space-y-2">
        {opts.map(o => (
          <div key={o.id} className={`rounded-sm p-2.5 bg-surface border ${o.sel ? 'border-accent border-2' : 'border-border'}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`font-mono text-[10px] ${o.sel ? 'text-accent' : 'text-muted'}`}>{o.id}</span>
              <span className="text-[12px] text-text font-medium">{o.label}</span>
              {o.sel && (
                <span className="font-mono text-[9px] text-approved border border-approved/40 px-1.5 py-[2px] rounded-sm tracking-widest">SELECTED ↓</span>
              )}
            </div>
            <div className="font-mono text-[10px] text-muted">risk {o.risk} · est {o.cost}</div>
          </div>
        ))}
        <div className="font-mono text-[10px] text-faint italic px-1 pt-1">selection ≠ approval · approval ≠ applied</div>
      </div>
    );
  } else if (id === 'selection') {
    body = (
      <div className="p-3 font-mono text-[12px] text-text leading-7">
        <div>selected · <span className="text-accent">opt-02</span></div>
        <div className="text-muted text-[11px]">draft + cross-check against contradictions log</div>
      </div>
    );
  } else if (id === 'governance') {
    body = (
      <div className="p-3 grid grid-cols-[110px_1fr] gap-x-2.5 gap-y-1 font-mono text-[11px]">
        <div className="text-faint">decision</div><div className="text-approved">✓ EXECUTION PERMITTED</div>
        <div className="text-faint">approval</div><div className="text-text">operator · explicit</div>
        <div className="text-faint">readiness</div><div className="text-text">4 / 4 pass</div>
        <div className="text-faint">risk</div><div className="text-pending">medium · canonical mutation</div>
        <div className="text-faint">note</div><div className="text-muted">approved ≠ applied</div>
      </div>
    );
  } else if (id === 'execution') {
    body = (
      <div className="m-3 p-2.5 rounded-sm bg-surface border border-border font-mono text-[12px] leading-7 text-text">
        <div className="text-muted">## Memory</div>
        <div>Memory stores useful, committed, retrievable knowledge.</div>
        <div>Memory does not define current truth.</div>
        <div>
          Canonical state may reference only <span className="bg-accent/25 px-1 rounded-sm">committed memory IDs</span>.
        </div>
      </div>
    );
  } else if (id === 'context') {
    body = <div className="p-3 font-mono text-[11px] text-text leading-7">assembled context bundle · 4 docs · 2 memory refs · 8,412 tokens</div>;
  } else if (id === 'evaluation') {
    body = (
      <div className="p-3 grid grid-cols-[110px_1fr] gap-x-2.5 gap-y-1 font-mono text-[11px]">
        <div className="text-faint">verdict</div><div className="text-approved">success</div>
        <div className="text-faint">coverage</div><div className="text-text">4 / 4 goals</div>
        <div className="text-faint">note</div><div className="text-muted">drift against basis is within tolerance</div>
      </div>
    );
  } else if (id === 'memory') {
    body = (
      <div className="p-3 font-mono text-[11px] leading-7 text-text">
        <div className="text-faint">candidates</div>
        <div className="pl-2">· mem#0112 — heat-pump vendor shortlist (pending evidence link)</div>
        <div className="text-faint mt-1.5">committed</div>
        <div className="pl-2">· mem#0093 — operator bundling preference</div>
      </div>
    );
  } else if (id === 'transition') {
    body = (
      <div className="p-3 font-mono text-[11px] leading-7 text-text">
        <div className="text-faint">from</div><div className="pl-2 text-muted">ARCHITECTURE.md @ rev 73</div>
        <div className="text-faint mt-1.5">to</div><div className="pl-2 text-text">ARCHITECTURE.md @ rev 74 (+ §Memory)</div>
        <div className="text-faint mt-1.5">basis</div><div className="pl-2 text-muted">evaluation verdict + memory commit</div>
      </div>
    );
  } else if (id === 'outcome') {
    body = <div className="p-3 font-mono text-[11px] text-text leading-7">artifacts normalized · 1 file touched · 214 tokens added</div>;
  } else {
    body = <div className="p-3 font-mono text-[11px] text-faint italic">—</div>;
  }
  return (
    <Subcard label="OUTPUT · layer result" kindTag={<TruthTag kind={layer.outputKind} />}>
      {body}
    </Subcard>
  );
}

export function LayerPanel({ layer, runId, open, onToggle }: Props) {
  const statusCls = statusColorClass(layer.status);
  return (
    <div
      className={`border rounded-sm bg-panel mb-2 overflow-hidden ${open ? 'border-border-strong' : 'border-border'}`}
    >
      <button
        onClick={onToggle}
        className={`w-full text-left px-4 py-2.5 flex items-center gap-2.5 ${open ? 'bg-surface border-b border-border' : 'bg-panel'} hover:bg-surface/60`}
      >
        <span className="font-mono text-[9px] text-faint w-2.5">{open ? '▾' : '▸'}</span>
        <span className={`font-mono text-[13px] w-3.5 text-center ${statusCls.split(' ')[0]}`}>{statusGlyph(layer.status)}</span>
        <span className="font-mono text-[11px] tracking-[.15em] uppercase text-text w-[110px] flex-none">{layer.label}</span>
        <span className="text-[12px] text-muted flex-1 whitespace-nowrap overflow-hidden text-ellipsis">{layer.sum}</span>
        <span className="font-mono text-[10px] text-faint">{layer.dur}</span>
      </button>
      {open && layer.status !== 'skipped' && (
        <div className="p-3.5">
          <LayerInput layerId={layer.id} runId={runId} />
          <LayerReasoning layerId={layer.id} />
          <LayerOutput layer={layer} />
        </div>
      )}
      {open && layer.status === 'skipped' && (
        <div className="p-3.5 text-[12px] text-faint italic">Layer was not invoked in this run.</div>
      )}
    </div>
  );
}
