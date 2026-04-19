import { useMemo, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useData } from '../lib/state/DataContext';

const NAV_SECTIONS = [
  { to: '/overview', label: 'overview', glyph: '◉' },
  { to: '/runs', label: 'runs', glyph: '↻' },
  { to: '/changes', label: 'changes', glyph: '⇄' },
  { to: '/memory', label: 'memory', glyph: '◆' },
  { to: '/health', label: 'health', glyph: '◈' },
  { to: '/lookup', label: 'lookup', glyph: '⌕' },
  { to: '/settings', label: 'settings', glyph: '⚙' },
];

export function Sidebar() {
  const { adapter, version } = useData();
  const projects = useMemo(() => adapter.listProjects(), [adapter, version]);
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const activeProjectId = params.projectId ?? projects[0]?.id;
  const activeWuId = params.workUnitId;
  const activeRunId = params.runId;

  const [openWu, setOpenWu] = useState<Record<string, boolean>>(() => ({
    [activeWuId ?? '']: true,
  }));

  const activeProject = projects.find(p => p.id === activeProjectId) ?? projects[0];

  return (
    <aside className="w-72 flex-shrink-0 bg-rail border-r border-border flex flex-col h-full">
      <div className="px-3.5 pt-3.5 pb-3 border-b border-border flex items-center gap-2.5">
        <div className="w-7 h-7 rounded bg-accent grid place-items-center font-mono text-[13px] font-semibold text-[#1a1816]">J</div>
        <div>
          <div className="font-mono text-[13px] text-text font-medium leading-tight">jeff</div>
          <div className="font-mono text-[9px] text-faint tracking-widest mt-0.5">v1 · OPERATOR</div>
        </div>
        <button
          onClick={() => navigate('/settings')}
          className="ml-auto text-[16px] text-muted hover:text-text"
          aria-label="settings"
        >
          ⚙
        </button>
      </div>

      {/* Primary nav */}
      <nav className="px-2 py-2 border-b border-border">
        {NAV_SECTIONS.map(s => (
          <NavLink
            key={s.to}
            to={s.to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-1.5 rounded-sm font-mono text-[11px] ${isActive ? 'bg-panel text-text' : 'text-muted hover:text-text hover:bg-panel/50'}`
            }
          >
            <span className="w-3 text-center text-faint">{s.glyph}</span>
            <span>{s.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Projects */}
      <div className="px-3 pt-3 pb-1 flex items-center justify-between">
        <div className="label-mono">PROJECTS</div>
        <button className="font-mono text-[10px] text-muted border border-border px-1.5 py-[2px] rounded-sm hover:border-border-strong">
          + new
        </button>
      </div>
      <div className="px-1.5">
        {projects.map(p => {
          const isActive = p.id === activeProject?.id;
          const anyBlocked = p.workUnits.some(wu => wu.runs.some(r => r.status === 'blocked' || r.status === 'escalated'));
          const anyActive = p.workUnits.some(wu => wu.runs.some(r => r.status === 'active'));
          const dotClass = anyActive ? 'bg-approved' : anyBlocked ? 'bg-blocked' : 'bg-faint';
          return (
            <div
              key={p.id}
              onClick={() => navigate(`/p/${p.id}`)}
              className={`px-2.5 py-2 my-0.5 rounded-sm cursor-pointer ${isActive ? 'bg-panel border border-border-strong' : 'border border-transparent hover:bg-panel/40'}`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotClass}`} />
                <div className={`font-mono text-[12px] ${isActive ? 'text-text font-medium' : 'text-muted'}`}>{p.label}</div>
                <div className="ml-auto font-mono text-[10px] text-faint">{p.workUnits.length}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Work units of active project */}
      {activeProject && (
        <>
          <div className="px-3 pt-3 pb-1 flex items-center justify-between">
            <div className="label-mono truncate">WORK UNITS · {activeProject.label}</div>
          </div>
          <div className="flex-1 overflow-auto px-1.5 pb-2">
            {activeProject.workUnits.length === 0 && (
              <div className="p-3.5 text-[12px] text-faint italic">No work units yet.</div>
            )}
            {activeProject.workUnits.map(wu => {
              const isOpen = !!openWu[wu.id];
              const anyBlocked = wu.runs.some(r => r.status === 'blocked');
              const anyActive = wu.runs.some(r => r.status === 'active');
              const dotClass = anyActive ? 'bg-approved' : anyBlocked ? 'bg-blocked' : 'bg-faint';
              return (
                <div key={wu.id}>
                  <div
                    onClick={() => setOpenWu({ ...openWu, [wu.id]: !isOpen })}
                    className="flex items-center gap-2 px-2.5 py-1.5 my-0.5 rounded-sm cursor-pointer hover:bg-panel/40"
                  >
                    <span className="font-mono text-[9px] text-faint w-2.5">{isOpen ? '▾' : '▸'}</span>
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotClass}`} />
                    <span className="flex-1 text-[12px] text-text leading-tight">{wu.label}</span>
                    <span className="font-mono text-[10px] text-faint">{wu.runs.length}</span>
                  </div>
                  {isOpen && (
                    <div className="mb-1">
                      {wu.runs.map(r => {
                        const isRunActive =
                          r.id === activeRunId && wu.id === activeWuId && activeProject.id === params.projectId;
                        const glyph =
                          r.status === 'done' ? '✓' : r.status === 'active' ? '●' : r.status === 'blocked' ? '✕' : r.status === 'degraded' ? '△' : '○';
                        const gCls =
                          r.status === 'done'
                            ? 'text-approved'
                            : r.status === 'active'
                            ? 'text-accent'
                            : r.status === 'blocked'
                            ? 'text-blocked'
                            : r.status === 'degraded'
                            ? 'text-degraded'
                            : 'text-faint';
                        return (
                          <Link
                            key={r.id}
                            to={`/p/${activeProject.id}/wu/${wu.id}/r/${encodeURIComponent(r.id)}`}
                            className={`flex items-center gap-2 px-2.5 py-1 my-0.5 ml-6 rounded-sm ${isRunActive ? 'bg-panel border border-border-strong' : 'border border-transparent hover:bg-panel/40'}`}
                          >
                            <span className={`font-mono text-[10px] w-2.5 text-center ${gCls}`}>{glyph}</span>
                            <span className="font-mono text-[10px] text-muted w-14 flex-none">{r.id}</span>
                            <span className="text-[11px] text-muted flex-1 truncate">{r.label}</span>
                          </Link>
                        );
                      })}
                      <Link
                        to={`/p/${activeProject.id}/wu/${wu.id}/new`}
                        className="block px-2.5 py-1 ml-6 my-0.5 font-mono text-[10px] text-faint hover:text-muted"
                      >
                        + new run
                      </Link>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      <div className="px-3.5 py-2.5 border-t border-border flex items-center gap-2">
        <div className="w-5 h-5 rounded-full bg-border" />
        <div className="text-[11px] text-muted">operator</div>
        <div className="ml-auto label-mono">{location.pathname.slice(0, 14)}</div>
      </div>
    </aside>
  );
}
