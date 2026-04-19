import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { Pill } from '../components/Pill';
import { TruthTag } from '../components/TruthTag';

export function NewRun() {
  const { projectId, workUnitId } = useParams();
  const navigate = useNavigate();
  const { adapter, version, refresh } = useData();
  const project = useMemo(() => (projectId ? adapter.getProject(projectId) : undefined), [adapter, projectId, version]);
  const [wuId, setWuId] = useState<string | undefined>(workUnitId ?? project?.workUnits[0]?.id);
  const [msg, setMsg] = useState('');

  if (!project) return <div className="p-8 text-muted">Project not found.</div>;

  const onSubmit = () => {
    if (!msg.trim() || !wuId) return;
    const r = adapter.createRun(project.id, wuId, msg);
    refresh();
    navigate(`/p/${project.id}/wu/${wuId}/r/${encodeURIComponent(r.id)}`);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[760px] mx-auto px-6 py-8">
        <div className="label-mono mb-1">NEW RUN</div>
        <div className="font-mono text-[13px] text-text mb-2">
          <b>{project.label}</b>
          <span className="mx-1.5 text-faint">/</span>
          <span className="text-accent">{wuId ?? '—'}</span>
        </div>
        <div className="text-[22px] text-text font-medium tracking-tight mb-2">Start a new run</div>
        <div className="text-[13px] text-muted leading-relaxed mb-6">
          Your input becomes a <b className="text-text">request</b>. Jeff will assemble truth-first context,
          generate 0–3 honest proposals, and only execute after governance passes.
        </div>

        <div className="label-mono mb-1.5">WORK UNIT</div>
        <div className="flex flex-wrap gap-1.5 mb-5">
          {project.workUnits.map(w => (
            <Pill key={w.id} active={wuId === w.id} tone={wuId === w.id ? 'accent' : 'default'} onClick={() => setWuId(w.id)}>
              {w.id}
            </Pill>
          ))}
          <Pill>+ new work unit</Pill>
        </div>

        <div className="label-mono mb-1.5">OPERATOR REQUEST</div>
        <textarea
          value={msg}
          onChange={e => setMsg(e.target.value)}
          placeholder="What should Jeff work on inside this work unit?"
          className="w-full min-h-[120px] p-3 border border-border-strong bg-panel text-text rounded-sm font-sans text-[14px] leading-relaxed outline-none focus:border-accent resize-y"
        />

        <div className="label-mono mt-5 mb-1.5">SUGGESTED</div>
        <div className="flex flex-wrap gap-1.5 mb-6">
          {[
            'continue draft where we stopped',
            'research planning engines',
            'review memory for contradictions',
            'synthesize recent evaluation',
          ].map(s => (
            <Pill key={s} onClick={() => setMsg(s)}>{s}</Pill>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled={!msg.trim() || !wuId}
            onClick={onSubmit}
            className={`font-mono text-[12px] px-4 py-2 rounded-sm font-medium ${msg.trim() && wuId ? 'bg-accent text-[#1a1816] hover:opacity-90' : 'bg-border text-faint cursor-not-allowed'}`}
          >
            submit · start run →
          </button>
          <Pill onClick={() => navigate(-1)}>cancel</Pill>
          <div className="ml-auto flex items-center gap-2">
            <TruthTag kind="local" />
            <span className="font-mono text-[10px] text-faint">submission is a request, not truth mutation</span>
          </div>
        </div>
      </div>
    </div>
  );
}
