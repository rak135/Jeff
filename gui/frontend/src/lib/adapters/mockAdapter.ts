import type { JeffAdapter } from './index';
import { projects as seedProjects, changes as seedChanges, healthSignals, memoryCandidates } from '../mocks/data';
import type { Project, ChangeProposal, Run } from '../contracts/types';

/**
 * Mock adapter.
 *
 * In-memory store seeded from mocks/data.ts. Mutations persist only for the
 * life of the page (no localStorage beyond nav/theme).
 *
 * Backing mode: 'mock'. All surfaces here are simulated; the UI should badge
 * them accordingly where the distinction matters (changes, health, memory).
 */
export function createMockAdapter(): JeffAdapter {
  let projects: Project[] = structuredClone(seedProjects);
  let changes: ChangeProposal[] = structuredClone(seedChanges);

  const findRun = (pid: string, wid: string, rid: string): Run | undefined => {
    return projects.find(p => p.id === pid)?.workUnits.find(w => w.id === wid)?.runs.find(r => r.id === rid);
  };

  return {
    meta: { mode: 'mock', version: '0.1.0' },
    listProjects: () => projects,
    getProject: id => projects.find(p => p.id === id),
    getRun: findRun,
    listChanges: () => changes,
    listHealth: () => healthSignals,
    listMemory: () => memoryCandidates,
    createRun: (pid, wid, msg) => {
      const id = '#r-' + String(Math.floor(Math.random() * 9000) + 1000);
      const newRun: Run = {
        id,
        label: msg.slice(0, 42) + (msg.length > 42 ? '…' : ''),
        status: 'active',
        ts: 'just now',
        operatorMsg: msg,
        layers: [
          { id: 'context', label: 'context', status: 'active', dur: '0.1s', sum: 'assembling…', outputKind: 'support' },
          { id: 'research', label: 'research', status: 'pending', dur: '—', sum: '—', outputKind: 'support' },
          { id: 'proposal', label: 'proposal', status: 'pending', dur: '—', sum: '—', outputKind: 'support' },
          { id: 'selection', label: 'selection', status: 'pending', dur: '—', sum: '—', outputKind: 'canonical' },
          { id: 'governance', label: 'governance', status: 'pending', dur: '—', sum: '—', outputKind: 'canonical' },
          { id: 'execution', label: 'execution', status: 'pending', dur: '—', sum: '—', outputKind: 'support' },
          { id: 'outcome', label: 'outcome', status: 'pending', dur: '—', sum: '—', outputKind: 'derived' },
          { id: 'evaluation', label: 'evaluation', status: 'pending', dur: '—', sum: '—', outputKind: 'canonical' },
          { id: 'memory', label: 'memory', status: 'pending', dur: '—', sum: '—', outputKind: 'memory' },
          { id: 'transition', label: 'transition', status: 'pending', dur: '—', sum: '—', outputKind: 'canonical' },
        ],
        readiness: { pass: 4, total: 4 },
        governance: { decision: 'pending', approver: 'auto', policy: 'default' },
        verdict: null,
      };
      projects = projects.map(p =>
        p.id !== pid
          ? p
          : {
              ...p,
              workUnits: p.workUnits.map(w =>
                w.id !== wid ? w : { ...w, runs: [newRun, ...w.runs] },
              ),
            },
      );
      return newRun;
    },
    approveChange: id => {
      changes = changes.map(c =>
        c.id !== id ? c : { ...c, status: c.status === 'awaiting_approval' ? 'approved' : c.status },
      );
      return changes.find(c => c.id === id);
    },
    rejectChange: id => {
      changes = changes.map(c => (c.id !== id ? c : { ...c, status: 'rejected' as const }));
      return changes.find(c => c.id === id);
    },
    retryRun: (pid, wid, rid) => {
      const run = findRun(pid, wid, rid);
      if (!run) return undefined;
      // Simulated retry: flip blocked → active, reset readiness.
      projects = projects.map(p =>
        p.id !== pid
          ? p
          : {
              ...p,
              workUnits: p.workUnits.map(w =>
                w.id !== wid
                  ? w
                  : {
                      ...w,
                      runs: w.runs.map(r =>
                        r.id !== rid
                          ? r
                          : { ...r, status: 'active', readiness: { pass: 4, total: 4 }, ts: 'just now' },
                      ),
                    },
              ),
            },
      );
      return findRun(pid, wid, rid);
    },
    revalidateContext: (pid, wid, rid) => {
      projects = projects.map(p =>
        p.id !== pid
          ? p
          : {
              ...p,
              workUnits: p.workUnits.map(w =>
                w.id !== wid
                  ? w
                  : {
                      ...w,
                      runs: w.runs.map(r =>
                        r.id !== rid
                          ? r
                          : {
                              ...r,
                              layers: r.layers.map(l =>
                                l.id === 'context' ? { ...l, status: 'done', sum: 'revalidated · fresh snapshot', dur: '0.2s' } : l,
                              ),
                            },
                      ),
                    },
              ),
            },
      );
    },
  };
}
