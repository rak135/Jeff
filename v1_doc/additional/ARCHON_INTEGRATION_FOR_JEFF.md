# ARCHON_INTEGRATION_FOR_JEFF.md

Status: návrh integrační architektury pro Jeff  
Authority: subordinate to `ARCHITECTURE.md`, `ORCHESTRATOR_SPEC.md`, `PLANNING_AND_RESEARCH_SPEC.md`, `VISION.md`, `RESEARCH_V2_ROADMAP.md`, `INTERFACE_OPERATOR_SPEC.md`, `POLICY_AND_APPROVAL_SPEC.md`  
Purpose: navrhnout, jak využít Archon pro Jeffa bez porušení Jeffovy canonical architecture

---

## 1. Executive summary

Archon **není vhodný jako backbone Jeffa**.

Je vhodný pouze jako:
- **externí coding executor** pro vybrané work units,
- **rychlý sandbox pro prototypování coding workflow**,
- **UX a operator-flow inspirace** pro Jeff CLI/GUI,
- případně **budoucí provider** v Jeff Action/Infrastructure vrstvě.

Doporučený princip je jednoduchý:

- **Jeff zůstává mozek, pravda a governance**
- **Archon je vnější pracovní stroj pro code-heavy execution**

To znamená:
- Jeff dál vlastní `state -> context -> proposal -> selection -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition`
- Archon smí být použit jen uvnitř Jeff `Action`/`Infrastructure` hranice jako bounded capability
- Archon workflow, approval gates, workflow state, session DB, worktree a UI nikdy nesmí být považovány za Jeff canonical truth, governance authority, ani orchestration authority

---

## 2. Co je Archon a proč je to architektonicky nebezpečné

Aktuální Archon je **workflow engine pro AI coding agents**. Je postavený kolem YAML workflows, orchestrátoru, AI assistant clients, platform adapters a isolation providers. Umí deterministické workflow fáze typu planning, implementation, validation, review, approval a PR creation, včetně loopů, approval nodes, isolated git worktrees a více operátorských povrchů.

To je silné pro coding automation.

To je zároveň problém, pokud by se to mělo stát Jeffovým středem.

Jeff je postavený jinak:
- truth-first, ne workflow-first,
- governance-first před execution,
- transition-only mutation,
- explicitní oddělení proposal / selection / action / governance / execution / outcome / evaluation / memory,
- orchestrator jako coordinator, ne hidden brain,
- workflow není v1 first-class canonical truth.

### Tvrdý závěr

Archon jako **nástroj** ano.
Archon jako **Jeff architecture** ne.

---

## 3. Co přesně je v Jeffovi zakázáno

Následující věci nesmíme porušit:

### 3.1 Zakázané backbone outsourcing

Jeff explicitně nesmí outsourcovat svůj backbone na:
- agent frameworks,
- orchestration frameworks,
- planner frameworks,
- hidden workflow engines.

Archon do této rizikové zóny spadá, pokud by začal vlastnit hlavní řízení Jeffa.

### 3.2 Workflow nesmí být canonical truth

Archon je workflow-centric. Jeff v1 není.
Workflow může být support coordination concept, ale nesmí se stát canonical truth, permission authority ani mutation authority.

### 3.3 Orchestrator nesmí převzít business semantiku

Archon orchestrator nesmí nahradit Jeff orchestrator ani Jeff governance. Jeff orchestrator smí pouze sekvenovat veřejné kontrakty, validovat handoffy a routovat explicitní výstupy.

### 3.4 Externí tooling je povolen jen jako bounded capability

Jeff smí používat externí systémy pouze tam, kde Jeff pořád vlastní význam:
- Jeff vlastní semantics,
- externí nástroj poskytuje capability,
- capability je wrapped behind Jeff-owned contracts.

---

## 4. Kde Archon pro Jeffa dává smysl

### 4.1 Recommended use: Archon jako external coding executor

Nejčistší varianta je:

1. Jeff udělá truth-first práci:
   - state read
   - context
   - proposal
   - selection
   - action formation
   - governance

2. Pokud je výsledkem **lawfully allowed code-heavy action**, Jeff `Action` layer zavolá Archon.

3. Archon udělá:
   - izolovaný worktree,
   - workflow run,
   - implementační kroky,
   - testy,
   - review,
   - případně PR creation.

4. Jeff převezme výsledky jako **support artifacts / evidence**, ne jako truth:
   - workflow run metadata,
   - event stream,
   - test output,
   - diff / patch,
   - PR URL,
   - review notes,
   - apply/result facts.

5. Jeff potom sám udělá:
   - outcome normalization,
   - evaluation,
   - memory handoff,
   - případný transition.

Tím zůstává zachovaný Jeff backbone.

### 4.2 Fast prototyping use: Archon jako sandbox pro workflow experimenty

Archon je vhodný pro rychlé ověření patternů typu:
- plan -> implement loop -> validate -> human review -> PR
- worktree isolation
- long-running coding loop s checkpointy
- operator review gate UX
- streaming live execution events

To je výborné pro experiment.

Ale experiment nesmí definovat Jeff semantics. Po otestování se musí pattern přepsat do Jeff language a Jeff boundaries.

### 4.3 UX inspiration use: Archon jako inspirace pro Jeff operator surface

Archon má dobré nápady pro:
- execution event stream,
- progress visibility,
- workflow timeline,
- live tool-call rendering,
- operator review surfaces,
- multi-surface access.

Tyto věci lze převzít jako UX inspiraci.

Nesmí se převzít jejich hidden semantics.

---

## 5. Kde Archon použít nesmíme

Archon nesmí vlastnit:
- Jeff canonical state
- Jeff transition law
- Jeff governance / approval / readiness semantics
- Jeff proposal / selection semantics
- Jeff outcome / evaluation semantics
- Jeff memory write discipline
- Jeff orchestration meaning
- Jeff interface truth semantics

Archon nesmí být:
- Jeff runtime backbone
- Jeff workflow truth layer
- Jeff policy engine
- Jeff approval source of truth
- Jeff mutation authority
- Jeff memory layer
- Jeff hidden autonomous brain

---

## 6. Doporučený integrační model

## 6.1 Jednovětý model

**Jeff rozhoduje, Archon provádí omezený coding workflow, Jeff znovu vyhodnocuje a teprve potom případně mutuje truth.**

## 6.2 Layer mapping

### Core
Archon sem nesmí.

Core dál vlastní:
- canonical state,
- project/work_unit/run truth,
- transitions,
- canonical refs.

### Governance
Archon sem nesmí jako autorita.

Governance dál vlastní:
- policy,
- approval,
- readiness,
- permission to start.

Archon approval nodes mohou existovat jen jako:
- support review gates uvnitř externího coding workflow,
- nebo být úplně vypnuté v Jeff-driven flows.

Nikdy nesmí nahradit Jeff approval/readiness.

### Cognitive
Archon sem nepatří.

Cognitive dál vlastní:
- context,
- research,
- proposal,
- selection,
- planning,
- evaluation.

### Action
Tady Archon dává smysl.

Action layer může mít execution path:
- `local_executor`
- `archon_executor`
- později jiné executory

Action vlastní:
- execution entry,
- execution result collection,
- outcome normalization input.

### Infrastructure
Tady bude Archon adapter.

Infrastructure má vlastnit:
- Archon CLI/API klient,
- config,
- process spawning,
- polling / event streaming,
- artifact collection,
- error mapping,
- auth / environment plumbing.

### Orchestration
Jeff orchestrator dál sekvenuje celý flow.

Archon workflow orchestration je **subordinate execution mechanism**, ne Jeff orchestration authority.

### Interface
Jeff interface může ukazovat Archon run jako support panel:
- external executor: Archon
- workflow id
- current node
- last event
- linked artifacts

Ale musí být jasně označeno:
- tohle není canonical truth,
- tohle není Jeff lifecycle truth,
- tohle je execution support / external run state.

### Memory
Archon nesmí psát do Jeff memory.

Může dodat support artifacts nebo signals.
Jen Jeff Memory module vytváří memory candidates.

---

## 7. Nejlepší konkrétní varianta: Jeff-driven, Archon-backed code execution

## 7.1 High-level flow

```text
trigger
-> state read
-> context
-> proposal
-> selection
-> action formation
-> governance
-> execution(adapter = archon)
-> outcome
-> evaluation
-> memory
-> transition
-> truthful operator result
```

## 7.2 Archon se spouští až po governance

To je klíčové.

Ne dřív.

Ne po selection.
Ne po planning.
Ne po „workflow says next step“. 

Archon se smí spustit až když Jeff má:
- konkrétní bounded action,
- approval satisfied pokud je potřeba,
- readiness current,
- explicitní execution entry.

## 7.3 Archon vrací support outputs, ne authority

Archon output musí být v Jeffu mapovaný jen na support třídy, např.:
- `external_execution_run_ref`
- `artifact_ref`
- `trace_ref`
- `evidence_ref`
- `review_note_ref`
- `external_status_snapshot`

Žádné z toho nesmí být canonical truth samo o sobě.

---

## 8. Doporučený package layout v Jeff repo

```text
jeff/
  infrastructure/
    archon/
      __init__.py
      config.py
      client.py
      contracts.py
      mapper.py
      artifacts.py
      errors.py
      telemetry.py
  action/
    executors/
      __init__.py
      archon_executor.py
      local_executor.py
  cognitive/
    evaluation.py                  # beze změny ownership
  orchestrator/
    runner.py                      # pouze nový lawful branch do Action execution provideru
  interface/
    json_views.py                  # external executor support projection
    render.py                      # support rendering
  tests/
    unit/infrastructure/test_archon_client.py
    unit/action/test_archon_executor.py
    integration/test_archon_execution_flow.py
    antidrift/test_archon_not_truth.py
```

### Ownership pravidla

- `jeff.infrastructure.archon.*` = čistě technická integrace
- `jeff.action.executors.archon_executor` = Jeff Action wrapper nad Archon capability
- žádná Archon semantika nesmí prosáknout do Core/Governance/Cognitive

---

## 9. Doporučené Jeff-owned kontrakty

## 9.1 ArchonExecutionRequest

```json
{
  "action_id": "act_...",
  "project_id": "proj_...",
  "work_unit_id": "wu_...",
  "run_id": "run_...",
  "objective": "bounded coding objective",
  "workflow_profile": "bugfix | feature | refactor | review_only",
  "repo_locator": "string",
  "base_branch": "string",
  "constraints": [
    "Do not widen scope",
    "Run project validation commands",
    "Do not auto-merge"
  ],
  "operator_approval_required_inside_archon": false,
  "collect_artifacts": true,
  "timeout_policy": "bounded"
}
```

### Pravidla
- Jeff formátuje request.
- Archon workflow file je implementation detail.
- `workflow_profile` je Jeff abstraction, ne Archon semantics leak.

## 9.2 ExternalExecutionRunRef

```json
{
  "executor_type": "archon",
  "external_run_id": "string",
  "workflow_name": "string",
  "started_at": "iso8601",
  "status": "running | waiting | completed | failed | blocked | unknown",
  "locator": "string | null"
}
```

### Pravidla
- `status` je external support status.
- Není to Jeff `execution_status`, `outcome_state`, ani `evaluation_verdict`.

## 9.3 ArchonArtifactBundle

```json
{
  "external_run_id": "string",
  "artifacts": [
    {
      "artifact_type": "diff | test_log | review_note | pr_link | workflow_log | changed_files",
      "locator": "string",
      "summary": "string"
    }
  ],
  "event_excerpt": [
    "workflow started",
    "tests failed on iteration 1",
    "tests passed on iteration 2",
    "review completed"
  ]
}
```

## 9.4 ArchonExecutionResult

```json
{
  "action_id": "act_...",
  "external_run_ref": {"executor_type": "archon", "external_run_id": "..."},
  "execution_status": "completed | completed_with_degradation | failed | interrupted | aborted",
  "artifacts": [],
  "warnings": [],
  "raw_external_status": "string",
  "observed_effect_notes": []
}
```

### Pravidla
- `execution_status` zde určuje Jeff Action wrapper na základě Jeff mapping rules.
- Nesmí to být slepě převzatý Archon status string.

---

## 10. Mapping rules: Archon -> Jeff

## 10.1 Co se mapuje přímo

Lze mapovat:
- external run id
- workflow name
- event stream
- artifact refs
- raw logs
- PR URL
- changed files
- validation/test outputs

## 10.2 Co se nesmí mapovat přímo

Nesmí se přímo mapovat:
- Archon approval => Jeff approval
- Archon workflow completed => Jeff outcome acceptable
- Archon PR created => Jeff objective completed
- Archon review passed => Jeff evaluation acceptable
- Archon event state => Jeff canonical lifecycle
- Archon DB/session state => Jeff current truth

## 10.3 Co musí projít Jeff re-judgment

Po návratu z Archonu Jeff musí znovu udělat:
- outcome normalization,
- evaluation,
- deterministic overrides,
- případně revalidation or operator escalation,
- teprve pak případný transition.

---

## 11. Governance pravidla pro Archon integration

## 11.1 Jeff governance je nadřazená

Jeff approval/readiness jsou jediná autorita pro start action.

Archon approval gates jsou pouze volitelné support mechanismy pro:
- vnější review,
- interaktivní refinement,
- human-in-the-loop coding flow.

### Doporučení
Pro první integraci:
- **vypnout Archon approval nodes v Jeff-driven flow**, nebo
- je povolit jen pro **internal support review**, ale ne jako start authority.

## 11.2 Revalidation before apply / merge

Pokud Archon workflow dojde až k bodu typu:
- create PR,
- apply patch,
- merge,
- deploy,

pak Jeff musí mít odděleně řešené:
- zda je to jen support artifact,
- zda vznikl `Change`,
- zda je potřeba nový governance pass,
- zda je potřeba revalidation.

Doporučení pro v1:
- Archon může vytvořit branch / diff / PR draft
- Archon **nemá auto-merge / auto-apply authority**
- finální apply-like kroky zůstanou pod Jeff change-control a governance discipline

---

## 12. Truthfulness rules na interface vrstvě

Jeff GUI/CLI může ukazovat Archon data jen jako:
- external execution panel,
- support timeline,
- artifacts,
- external workflow snapshot.

Musí být explicitně odlišeno:

### Canonical truth
- current project/work_unit/run truth
- current Jeff lifecycle truth
- governance status
- outcome/evaluation/transition truth

### External support
- Archon workflow state
- Archon node timeline
- Archon logs
- Archon worktree / branch / PR artifacts

Nesmí vzniknout UI lež typu:
- „Approved“ protože to řekl Archon node
- „Completed“ protože doběhl workflow
- „Done“ protože vznikl PR

---

## 13. Smallest useful prototype

Nejmenší užitečný prototype bych dělal v tomto pořadí:

### Phase A — sandbox mimo Jeff truth
Založ si izolovaný experiment:
- jeden repo-level Archon workflow pro bugfix/feature,
- worktree isolation,
- test run,
- review step,
- PR draft creation.

Cíl:
- zjistit, jak kvalitně Archon zvládá coding loop,
- jaké artifacts a events vrací,
- jak vypadá jeho failure surface.

### Phase B — Jeff Infrastructure adapter
Implementuj čistě technickou vrstvu:
- spawn Archon command / API,
- read workflow run id,
- poll status,
- collect artifacts,
- normalize errors.

Bez zásahu do Core/Governance semantics.

### Phase C — Jeff Action executor
Přidej `archon_executor` jako volitelný executor pro code-heavy actions.

Cíl:
- Jeff action -> archon request,
- archon result -> Jeff execution result.

### Phase D — truthful operator surface
Přidej support panel do CLI/GUI:
- external executor,
- workflow name,
- node progress,
- artifact refs.

### Phase E — evaluation + change-control integration
Teprve potom řeš:
- PR draft handling,
- change support flows,
- revalidation,
- stronger review loops.

---

## 14. Co bych naopak nedělal

Nedělej tyhle chyby:

### 14.1 Nepřepisuj Jeff orchestrator na Archon workflows
To je přímá cesta k workflow inflation.

### 14.2 Nezaveď YAML jako Jeff control-plane truth
YAML workflow může být execution recipe pro Archon, ne Jeff semantics.

### 14.3 Nenech Archon approval nahradit Jeff governance
To by rozbilo approval/readiness boundary.

### 14.4 Nenech Archon session DB stát se Jeff history truth
Je to external system record, ne Jeff canonical store.

### 14.5 Neleakuj Archon pojmy do Jeff glossary
Jeff má vlastní slovník. Nepřepisuj ho podle cizího harnessu.

---

## 15. Rozhodnutí podle use-case

## 15.1 Kdy Archon použít

Použij Archon když je work unit hlavně:
- code generation / refactor,
- implementační loop nad repo,
- test-fix loop,
- review + PR preparation,
- worktree-isolated multi-branch experimentation.

## 15.2 Kdy Archon nepoužít

Nepoužívej Archon pro:
- canonical state work,
- governance judgments,
- selection,
- memory,
- research semantics,
- evaluation semantics,
- non-coding bounded work, kde by workflow engine byl zbytečný balvan.

---

## 16. Budoucí rozšíření

Pokud se Archon osvědčí, může se později rozšířit na:
- více `workflow_profile` typů,
- richer external execution telemetry,
- branch-per-work-unit execution strategy,
- PR draft review pipeline,
- optional human review inside external coding flow,
- richer GUI execution timeline.

Ale stále jen za těchto podmínek:
- Jeff vlastní semantics,
- Jeff vlastní governance,
- Jeff vlastní truth,
- Jeff vlastní evaluation,
- Jeff vlastní transition.

---

## 17. Final recommendation

Správný směr je:

### Ano
- použít Archon jako bounded external coding executor,
- použít Archon jako rychlý workflow sandbox,
- převzít z něj worktree isolation, event streaming a některé operator UX nápady.

### Ne
- nestavět na Archonu Jeff architecture,
- neudělat z Archonu Jeff orchestrator,
- nepřevzít jeho workflow model jako Jeff control plane,
- nepustit jeho approval/workflow/session vrstvu do Jeff truth nebo governance law.

### Doporučené rozhodnutí

**Implementovat Archon nejdřív jako experimentální `archon_executor` v Infrastructure + Action boundary.**

To je nejčistší varianta.
Není to chaos.
Není to přestavba Jeffa podle cizího harnessu.
A zároveň to dává reálnou praktickou hodnotu.

---

## 18. Suggested next implementation pass

Pokud půjdeš dál hned, doporučuji udělat jediný úzký pass:

1. navrhnout `jeff/infrastructure/archon/contracts.py`
2. navrhnout `jeff/infrastructure/archon/client.py`
3. navrhnout `jeff/action/executors/archon_executor.py`
4. přidat anti-drift testy:
   - Archon output is never canonical truth
   - Archon approval is never Jeff approval
   - Archon workflow completion is never evaluation success
   - Archon external state is rendered as support only

To je správný první implementační řez.

---

## 19. References

### Jeff canonical docs
- `ARCHITECTURE.md`
- `ORCHESTRATOR_SPEC.md`
- `PLANNING_AND_RESEARCH_SPEC.md`
- `VISION.md`
- `RESEARCH_V2_ROADMAP.md`

### Official Archon sources consulted
- GitHub repository: https://github.com/coleam00/Archon
- Architecture docs: https://archon.diy/reference/architecture/
- Workflow authoring docs: https://archon.diy/guides/authoring-workflows/

