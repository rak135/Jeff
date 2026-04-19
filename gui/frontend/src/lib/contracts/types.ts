/**
 * Jeff frontend domain contracts.
 *
 * These types are intentionally aligned with the vocabulary Jeff backend uses
 * (see jeff/cognitive/*, v1_doc/ARCHITECTURE.md, INTERFACE_OPERATOR_SPEC.md).
 *
 * NOTE: this prototype covers surfaces that do not yet exist in backend — those
 * are marked `future` in the `backing` field so the UI can badge them honestly.
 * When real backend providers land, adapter implementations swap in (see
 * lib/adapters/), these contracts remain stable.
 */

export type Backing = 'real' | 'future' | 'mock';

export type TruthClass = 'canonical' | 'support' | 'derived' | 'memory' | 'local';

export type RunStatus =
  | 'active'       // execution in progress
  | 'pending'      // queued, not yet started
  | 'done'         // completed successfully (evaluation verdict = success)
  | 'blocked'      // honest escalation — readiness/governance stopped the run
  | 'degraded'     // completed with evaluation verdict = degraded/partial
  | 'inconclusive' // evaluation could not decide
  | 'deferred'     // operator-deferred
  | 'escalated'    // escalated to operator attention
  | 'stalled';     // stuck without honest escalation signal

export type LayerId =
  | 'context'
  | 'research'
  | 'proposal'
  | 'selection'
  | 'governance'
  | 'execution'
  | 'outcome'
  | 'evaluation'
  | 'memory'
  | 'transition';

export type LayerStatus = 'done' | 'active' | 'pending' | 'blocked' | 'skipped' | 'degraded';

export interface LayerFrame {
  id: LayerId;
  label: string;
  status: LayerStatus;
  dur: string;
  sum: string;
  /** Derived summary of layer inputs — SUPPORT class (not truth). */
  inputs?: Array<[string, string, TruthClass?]>;
  /** Reasoning stream events — DERIVED (reconstructed from telemetry). */
  reasoning?: Array<{ kind: 'note' | 'ok' | 'warn' | 'think' | 'stream'; text: string }>;
  /** Layer output. Truth class depends on layer. */
  outputKind: TruthClass;
}

export interface Run {
  id: string;
  label: string;
  status: RunStatus;
  ts: string;
  operatorMsg: string;
  /** Layers populated by lifecycle — backing `real` once orchestrator run view lands. */
  layers: LayerFrame[];
  /** Evaluation verdict if terminal. */
  verdict?: 'success' | 'degraded' | 'partial' | 'inconclusive' | null;
  /** Readiness checks snapshot at time of run. */
  readiness?: { pass: number; total: number; failing?: string[] };
  /** Governance decision. */
  governance?: {
    decision: 'permitted' | 'denied' | 'pending';
    approver: 'operator' | 'auto';
    policy: string;
    note?: string;
  };
  /** Change proposal derived from this run, if any. */
  changeId?: string;
}

export interface WorkUnit {
  id: string;
  label: string;
  runs: Run[];
}

export interface Project {
  id: string;
  label: string;
  sub: string;
  workUnits: WorkUnit[];
}

/** Change-control surface — future-facing. */
export interface ChangeProposal {
  id: string;
  projectId: string;
  workUnitId: string;
  runId: string;
  title: string;
  kind: 'canonical_spec' | 'policy' | 'memory_commit' | 'artifact' | 'transition';
  status: 'draft' | 'awaiting_approval' | 'approved' | 'applied' | 'rejected' | 'withdrawn';
  createdAt: string;
  diff: Array<{ path: string; before?: string; after?: string }>;
  backing: Backing;
}

/** Health / telemetry surfaces — future-facing. */
export interface HealthSignal {
  id: string;
  name: string;
  severity: 'ok' | 'degraded' | 'blocked' | 'pending';
  scope: string;
  detail: string;
  backing: Backing;
}

/** Memory candidate — backed by memory/write_pipeline once wired. */
export interface MemoryCandidate {
  id: string;
  text: string;
  sourceRunId: string;
  evidenceLink?: string;
  status: 'candidate' | 'committed' | 'rejected';
  truth: TruthClass; // always 'memory' in practice
}

export interface ProviderMeta {
  mode: 'mock' | 'hybrid' | 'future-live-placeholder';
  version: string;
}
