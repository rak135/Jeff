import { useParams } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';
import { useTheme } from '../lib/state/ThemeContext';

export function TopBar() {
  const { adapter } = useData();
  const { theme, setTheme } = useTheme();
  const params = useParams();
  const project = params.projectId ? adapter.getProject(params.projectId) : undefined;
  const wu = project?.workUnits.find(w => w.id === params.workUnitId);
  const run = wu?.runs.find(r => r.id === params.runId);

  return (
    <header className="h-11 flex-shrink-0 bg-panel border-b border-border flex items-center gap-3 px-4">
      <div className="font-mono text-[10px] text-faint tracking-widest">SCOPE</div>
      <nav className="flex items-center gap-1.5 font-mono text-[12px]">
        <span className="text-muted">operator</span>
        <span className="text-faint">/</span>
        <span className={project ? 'text-text' : 'text-faint'}>{project?.label ?? '—'}</span>
        {wu && (
          <>
            <span className="text-faint">/</span>
            <span className="text-accent">{wu.id}</span>
          </>
        )}
        {run && (
          <>
            <span className="text-faint">/</span>
            <span className="text-text">{run.id}</span>
          </>
        )}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <div className="flex items-center gap-1.5 font-mono text-[10px] text-muted">
          <span className="w-1.5 h-1.5 rounded-full bg-approved" />
          source · {adapter.meta.mode}
        </div>
        <div className="flex items-center gap-0.5 bg-surface border border-border rounded-sm p-0.5">
          {(['light', 'dark'] as const).map(v => (
            <button
              key={v}
              onClick={() => setTheme(v)}
              className={`font-mono text-[10px] px-2 py-0.5 rounded-sm tracking-wide ${theme === v ? 'bg-accent text-[#1a1816]' : 'text-muted hover:text-text'}`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
