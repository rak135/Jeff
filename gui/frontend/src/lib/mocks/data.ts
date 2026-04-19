import type {
  Project,
  ChangeProposal,
  HealthSignal,
  MemoryCandidate,
  LayerFrame,
  Run,
} from '../contracts/types';

/**
 * Mock/simulated data store.
 *
 * Everything here is simulated. When backend surfaces exist, the mock adapter
 * in lib/adapters/mockAdapter.ts is replaced (or composed) with a real provider.
 *
 * Keep the data shape authentic — no lorem ipsum.
 */

function layersDone(): LayerFrame[] {
  return [
    { id: 'context', label: 'context', status: 'done', dur: '0.4s', sum: '3 docs · 1 memory ref', outputKind: 'support' },
    { id: 'research', label: 'research', status: 'done', dur: '3m 02s', sum: '5 sources · 9 claims', outputKind: 'support' },
    { id: 'proposal', label: 'proposal', status: 'done', dur: '22s', sum: '3 options', outputKind: 'support' },
    { id: 'selection', label: 'selection', status: 'done', dur: '8s', sum: 'opt-01', outputKind: 'canonical' },
    { id: 'governance', label: 'governance', status: 'done', dur: '0.9s', sum: 'auto · readiness 4/4', outputKind: 'canonical' },
    { id: 'execution', label: 'execution', status: 'done', dur: '1m 11s', sum: 'completed', outputKind: 'support' },
    { id: 'outcome', label: 'outcome', status: 'done', dur: '0.2s', sum: 'artifacts normalized', outputKind: 'derived' },
    { id: 'evaluation', label: 'evaluation', status: 'done', dur: '0.4s', sum: 'verdict · success', outputKind: 'canonical' },
    { id: 'memory', label: 'memory', status: 'done', dur: '0.3s', sum: '1 candidate · 1 committed', outputKind: 'memory' },
    { id: 'transition', label: 'transition', status: 'done', dur: '0.2s', sum: 'truth updated', outputKind: 'canonical' },
  ];
}

function layersActive(): LayerFrame[] {
  return [
    { id: 'context', label: 'context', status: 'done', dur: '0.4s', sum: '4 docs · 2 memory refs', outputKind: 'support' },
    { id: 'research', label: 'research', status: 'done', dur: '2m 14s', sum: '4 sources · 7 claims', outputKind: 'support' },
    { id: 'proposal', label: 'proposal', status: 'done', dur: '18s', sum: '2 honest options', outputKind: 'support' },
    { id: 'selection', label: 'selection', status: 'done', dur: '6s', sum: 'opt-02 · cross-check path', outputKind: 'canonical' },
    { id: 'governance', label: 'governance', status: 'done', dur: '1.2s', sum: 'approved · readiness 4/4', outputKind: 'canonical' },
    { id: 'execution', label: 'execution', status: 'active', dur: '1m 48s', sum: 'drafting §Memory', outputKind: 'support' },
    { id: 'outcome', label: 'outcome', status: 'pending', dur: '—', sum: '—', outputKind: 'derived' },
    { id: 'evaluation', label: 'evaluation', status: 'pending', dur: '—', sum: '—', outputKind: 'canonical' },
    { id: 'memory', label: 'memory', status: 'pending', dur: '—', sum: '0 candidates', outputKind: 'memory' },
    { id: 'transition', label: 'transition', status: 'pending', dur: '—', sum: 'no truth change yet', outputKind: 'canonical' },
  ];
}

function layersBlocked(): LayerFrame[] {
  return [
    { id: 'context', label: 'context', status: 'done', dur: '0.3s', sum: 'snapshot loaded', outputKind: 'support' },
    { id: 'research', label: 'research', status: 'skipped', dur: '—', sum: 'not invoked', outputKind: 'support' },
    { id: 'proposal', label: 'proposal', status: 'skipped', dur: '—', sum: 'not invoked', outputKind: 'support' },
    { id: 'selection', label: 'selection', status: 'skipped', dur: '—', sum: 'not invoked', outputKind: 'canonical' },
    { id: 'governance', label: 'governance', status: 'blocked', dur: '0.6s', sum: 'readiness fail · stale basis + unresolved conflict', outputKind: 'canonical' },
    { id: 'execution', label: 'execution', status: 'skipped', dur: '—', sum: 'no permit', outputKind: 'support' },
    { id: 'outcome', label: 'outcome', status: 'skipped', dur: '—', sum: '—', outputKind: 'derived' },
    { id: 'evaluation', label: 'evaluation', status: 'skipped', dur: '—', sum: '—', outputKind: 'canonical' },
    { id: 'memory', label: 'memory', status: 'skipped', dur: '—', sum: '—', outputKind: 'memory' },
    { id: 'transition', label: 'transition', status: 'skipped', dur: '—', sum: 'no truth change', outputKind: 'canonical' },
  ];
}

function makeRun(
  id: string,
  label: string,
  status: Run['status'],
  ts: string,
  operatorMsg: string,
  extra: Partial<Run> = {},
): Run {
  const layers =
    status === 'active'
      ? layersActive()
      : status === 'blocked'
      ? layersBlocked()
      : layersDone();
  return {
    id,
    label,
    status,
    ts,
    operatorMsg,
    layers,
    readiness:
      status === 'blocked'
        ? { pass: 2, total: 4, failing: ['stale basis', 'unresolved contradiction'] }
        : { pass: 4, total: 4 },
    governance:
      status === 'blocked'
        ? { decision: 'denied', approver: 'auto', policy: 'mutate_canonical_spec', note: 'readiness check failed' }
        : status === 'active'
        ? { decision: 'permitted', approver: 'operator', policy: 'mutate_canonical_spec', note: 'approved ≠ applied' }
        : { decision: 'permitted', approver: 'auto', policy: 'default_spec_edit' },
    verdict: status === 'done' ? 'success' : status === 'degraded' ? 'degraded' : null,
    ...extra,
  };
}

export const projects: Project[] = [
  {
    id: 'jeff',
    label: 'jeff',
    sub: 'personal work system',
    workUnits: [
      {
        id: 'define-architecture',
        label: 'define canonical ARCHITECTURE.md',
        runs: [
          makeRun(
            '#r-0147',
            'draft Memory section',
            'active',
            '4m ago',
            'Draft the Memory section of ARCHITECTURE.md using the committed memory spec. Keep the distinction between memory and canonical state explicit.',
            { changeId: 'chg-0041' },
          ),
          makeRun('#r-0146', 'continue draft', 'blocked', '17m ago', 'Continue the draft from where we stopped.'),
          makeRun('#r-0145', 'research workflow-as-truth', 'done', '1h ago', 'Research whether workflow should be a first-class truth object.'),
          makeRun('#r-0144', 'scoping pass', 'done', '3h ago', 'Scope the ARCHITECTURE rewrite.'),
        ],
      },
      {
        id: 'memory-spec',
        label: 'memory spec draft',
        runs: [makeRun('#r-0139', 'initial outline', 'done', '2h ago', 'Outline MEMORY_SPEC.md.')],
      },
      {
        id: 'policy-matrix',
        label: 'policy & approval matrix',
        runs: [makeRun('#r-0131', 'draft matrix', 'blocked', 'yesterday', 'Draft the policy + approval matrix.')],
      },
      {
        id: 'observability',
        label: 'telemetry & health signals',
        runs: [
          makeRun('#r-0128', 'enumerate run signals', 'degraded', '2d ago', 'Enumerate the health signals we want exposed on the run surface.'),
        ],
      },
    ],
  },
  {
    id: 'home_energy_upgrade',
    label: 'home_energy_upgrade',
    sub: 'research · heat pumps',
    workUnits: [
      {
        id: 'heat-pump-research',
        label: 'research heat-pump options',
        runs: [makeRun('#r-0051', 'survey 3 vendors', 'done', 'yesterday', 'Survey heat-pump options available in EU.')],
      },
    ],
  },
  {
    id: 'book_research',
    label: 'book_research',
    sub: 'evidence synthesis',
    workUnits: [],
  },
  {
    id: 'client_proposal',
    label: 'client_proposal',
    sub: 'draft · blocked',
    workUnits: [
      {
        id: 'proposal-draft',
        label: 'draft proposal document',
        runs: [
          makeRun('#r-0022', 'initial draft', 'blocked', '2d ago', 'Draft client proposal for Acme.'),
          makeRun('#r-0021', 'scope', 'stalled', '3d ago', 'Establish scope of the proposal.'),
        ],
      },
    ],
  },
];

export const changes: ChangeProposal[] = [
  {
    id: 'chg-0041',
    projectId: 'jeff',
    workUnitId: 'define-architecture',
    runId: '#r-0147',
    title: 'ARCHITECTURE.md · add §Memory section',
    kind: 'canonical_spec',
    status: 'awaiting_approval',
    createdAt: '4m ago',
    backing: 'future',
    diff: [
      {
        path: 'v1_doc/ARCHITECTURE.md',
        before: '## Runtime\n…',
        after:
          '## Runtime\n…\n\n## Memory\nMemory stores useful, committed, retrievable knowledge.\nMemory does not define current truth.\nCanonical state may reference only committed memory IDs.',
      },
    ],
  },
  {
    id: 'chg-0040',
    projectId: 'jeff',
    workUnitId: 'memory-spec',
    runId: '#r-0139',
    title: 'MEMORY_SPEC.md · outline draft',
    kind: 'canonical_spec',
    status: 'applied',
    createdAt: '2h ago',
    backing: 'future',
    diff: [{ path: 'v1_doc/MEMORY_SPEC.md', after: '# MEMORY_SPEC\n\n§1 …' }],
  },
  {
    id: 'chg-0039',
    projectId: 'jeff',
    workUnitId: 'policy-matrix',
    runId: '#r-0131',
    title: 'POLICY_SPEC.md · section 4 edits',
    kind: 'policy',
    status: 'rejected',
    createdAt: 'yesterday',
    backing: 'future',
    diff: [{ path: 'v1_doc/POLICY_AND_APPROVAL_SPEC.md', before: '§4 …', after: '§4 (revised) …' }],
  },
];

export const healthSignals: HealthSignal[] = [
  { id: 'h1', name: 'readiness · stale basis', severity: 'blocked', scope: 'jeff / policy-matrix', detail: 'Context is 2 runs behind canonical state.', backing: 'future' },
  { id: 'h2', name: 'contradiction · mem#0093 ↔ POLICY §4.2', severity: 'blocked', scope: 'jeff / define-architecture', detail: 'Memory commit contradicts canonical policy.', backing: 'future' },
  { id: 'h3', name: 'degraded evaluation · r-0128', severity: 'degraded', scope: 'jeff / observability', detail: 'Evaluation returned partial coverage.', backing: 'future' },
  { id: 'h4', name: 'stalled run · r-0021', severity: 'pending', scope: 'client_proposal / proposal-draft', detail: 'No progress for > 24h, no escalation signal.', backing: 'future' },
  { id: 'h5', name: 'memory write pipeline', severity: 'ok', scope: 'global', detail: 'All commits validated.', backing: 'future' },
];

export const memoryCandidates: MemoryCandidate[] = [
  {
    id: 'mem#0093',
    text: 'Operator prefers one bundled PR for refactors in cognitive/ over many small ones.',
    sourceRunId: '#r-0139',
    evidenceLink: 'runs/#r-0139#transcript',
    status: 'committed',
    truth: 'memory',
  },
  {
    id: 'mem#0112',
    text: 'Heat-pump vendor shortlist: three EU suppliers with EN 14511 certification.',
    sourceRunId: '#r-0051',
    evidenceLink: 'runs/#r-0051',
    status: 'candidate',
    truth: 'memory',
  },
];
