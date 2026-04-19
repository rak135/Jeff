import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { TruthTag } from '../components/TruthTag';
import { StatusChip, Dot } from '../components/StatusChip';

export function ProjectView() {
  const { projectId } = useParams();
  const { adapter, version } = useData();
  const project = useMemo(() => (projectId ? adapter.getProject(projectId) : undefined), [adapter, projectId, version]);

  if (!project) return <div className="p-8 text-muted">Project not found.</div>;

  if (project.workUnits.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="max-w-lg text-center">
          <div className="label-mono mb-2">PROJECT · {project.label.toUpperCase()}</div>
          <div className="text-[22px] text-text font-medium mb-2">Nothing here yet.</div>
          <div className="text-[13px] text-muted leading-relaxed mb-4">
            Projects are hard isolation boundaries. Start a work unit to begin.
          </div>
          <Link to={`/p/${project.id}/new`} className="inline-block bg-accent text-[#1a1816] font-mono text-[12px] px-4 py-2 rounded-sm">+ new run</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1100px] mx-auto px-6 py-6 space-y-4">
        <div>
          <div className="label-mono mb-1">PROJECT</div>
          <div className="text-[22px] text-text font-medium tracking-tight">{project.label}</div>
          <div className="text-[13px] text-muted">{project.sub}</div>
        </div>

        {project.workUnits.map(wu => (
          <PanelCard
            key={wu.id}
            title={wu.id}
            truth={<TruthTag kind="canonical" />}
            right={
              <Link to={`/p/${project.id}/wu/${wu.id}/new`} className="font-mono text-[10px] text-muted hover:text-text">+ new run</Link>
            }
          >
            <div className="px-4 pt-2 pb-1 text-[13px] text-text">{wu.label}</div>
            <div className="divide-y divide-border">
              {wu.runs.map(r => (
                <Link
                  key={r.id}
                  to={`/p/${project.id}/wu/${wu.id}/r/${encodeURIComponent(r.id)}`}
                  className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-surface"
                >
                  <Dot status={r.status} />
                  <span className="font-mono text-[10px] text-muted w-16">{r.id}</span>
                  <span className="text-[12px] text-text flex-1 truncate">{r.label}</span>
                  <span className="font-mono text-[10px] text-faint">{r.ts}</span>
                  <StatusChip status={r.status} />
                </Link>
              ))}
            </div>
          </PanelCard>
        ))}
      </div>
    </div>
  );
}

export function WorkUnitView() {
  const { projectId, workUnitId } = useParams();
  const { adapter, version } = useData();
  const project = useMemo(() => (projectId ? adapter.getProject(projectId) : undefined), [adapter, projectId, version]);
  const wu = project?.workUnits.find(w => w.id === workUnitId);

  if (!project || !wu) return <div className="p-8 text-muted">Work unit not found.</div>;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1100px] mx-auto px-6 py-6 space-y-4">
        <div className="flex items-end gap-3">
          <div>
            <div className="label-mono mb-1">{project.label} / WORK UNIT</div>
            <div className="text-[22px] text-text font-medium tracking-tight">{wu.label}</div>
            <div className="font-mono text-[11px] text-muted mt-1">{wu.id} · {wu.runs.length} runs</div>
          </div>
          <TruthTag kind="canonical" />
          <Link to={`/p/${project.id}/wu/${wu.id}/new`} className="ml-auto bg-accent text-[#1a1816] font-mono text-[11px] px-3 py-1.5 rounded-sm">+ new run</Link>
        </div>

        <PanelCard title="RUN HISTORY">
          <div className="divide-y divide-border">
            {wu.runs.map(r => (
              <Link
                key={r.id}
                to={`/p/${project.id}/wu/${wu.id}/r/${encodeURIComponent(r.id)}`}
                className="flex items-center gap-3 px-4 py-3 hover:bg-surface"
              >
                <Dot status={r.status} />
                <span className="font-mono text-[10px] text-muted w-16">{r.id}</span>
                <span className="text-[12px] text-text flex-1 truncate">{r.label}</span>
                <span className="font-mono text-[10px] text-faint">{r.ts}</span>
                <StatusChip status={r.status} />
              </Link>
            ))}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
