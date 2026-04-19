import type {
  Project,
  ChangeProposal,
  HealthSignal,
  MemoryCandidate,
  ProviderMeta,
  Run,
} from '../contracts/types';

/**
 * Adapter surface — the single place the UI reads domain state from.
 *
 * To wire real Jeff backend:
 *   1. Implement this interface against actual endpoints (e.g. jeff/interface/json_views.py
 *      exposed over HTTP).
 *   2. Swap the provider in DataContext.tsx by setting provider mode to 'hybrid'
 *      or 'future-live-placeholder' and routing calls through your new adapter.
 *   3. Keep the contracts stable — add new fields as optional, do not break existing.
 *
 * The UI must not read mock data directly; it reads through this seam.
 */
export interface JeffAdapter {
  meta: ProviderMeta;
  listProjects(): Project[];
  getProject(id: string): Project | undefined;
  getRun(projectId: string, workUnitId: string, runId: string): Run | undefined;
  listChanges(): ChangeProposal[];
  listHealth(): HealthSignal[];
  listMemory(): MemoryCandidate[];
  /** Mutations — in mock mode they mutate the in-memory store. */
  createRun(projectId: string, workUnitId: string, message: string): Run;
  approveChange(changeId: string): ChangeProposal | undefined;
  rejectChange(changeId: string): ChangeProposal | undefined;
  retryRun(projectId: string, workUnitId: string, runId: string): Run | undefined;
  revalidateContext(projectId: string, workUnitId: string, runId: string): void;
}

export { createMockAdapter } from './mockAdapter';
