# roadmap.md

# Jeff Roadmap — cesta od dnešního stavu k bounded autonomii

## Účel

Tento dokument popisuje realistickou cestu od současného stavu Jeffa k pozdější bounded autonomii.

Nejde o wish-list.
Jde o sequenced build order, který:

- staví na tom, co už opravdu funguje
- drží modulární hranice
- neotevírá broad rewrites
- zvyšuje schopnosti Jeffa po vrstvách
- zachovává truth-first backbone

---

# 1. Kde jsme teď

## Co už je skutečně hotové nebo dostatečně živé

### A. Research vertical je první reálně funkční modelová vrstva
Jeff dnes umí živý 3-step research flow:

1. Step 1 bounded text synthesis
2. Step 2 deterministic transform
3. Step 3 formatter fallback

K tomu je hotové:

- bounded syntax contract
- deterministic parser/normalizer
- formatter fallback bridge
- fail-closed provenance
- citation-key remap
- persistence support artifactů
- memory handoff boundary
- live CLI research runs
- prompt centralization pro Step 1 a Step 3

### B. Infrastructure má reuse backbone
Jeff dnes má:

- model adapters
- runtime config
- purpose vocabulary
- output strategy vocabulary
- capability profiles
- thin `ContractRuntime`
- research active path přes `ContractRuntime`

### C. Legacy debt v research byla z velké části odstraněna
Hotové:

- odstranění repair-era compat surface
- odstranění `ResearchResult`
- odstranění `legacy.py`
- orchestrator validation už používá `ResearchArtifact`

### D. Test suite je zelená
To je důležitý stabilizační checkpoint.
Neznamená to, že je hotová autonomie.
Znamená to, že backbone není momentálně rozbitý.

---

# 2. Co ještě nemáme

## Chybějící vrstvy pro bounded autonomii

Research sám o sobě nestačí.
Jeff zatím není autonomní systém.
Je to disciplinovaný research + infrastructure backbone.

Aby vznikla bounded autonomie, chybí hlavně:

- modelově/hybridně použitelná Proposal vrstva
- Selection vrstva napojená na real proposal outputs
- Evaluation vrstva jako skutečný rozhodovací výstup po execution
- Action/Governance wiring pro controlled execution
- durable state
- durable memory
- production orchestrator flows nad reálnými handlery
- continuity přes více runů

---

# 3. Cílový princip

Jeff nebude „autonomní“ tím, že necháme model dlouho běžet.

Jeff bude bounded autonomní tehdy, když bude umět:

1. přečíst truth state
2. složit kontext
3. případně udělat research
4. navrhnout bounded možnosti
5. vybrat / odmítnout / eskalovat
6. projít governance
7. provést bounded action
8. vyhodnotit výsledek
9. zapsat continuity do memory
10. lawfully mutovat truth přes transitions
11. pokračovat přes další run bez skrytých loopů

---

# 4. Architektonické zásady pro další cestu

## 4.1 Truth-first
- truth je v core state
- memory není truth
- research artifact není truth
- interface není truth
- LLM nikdy nepíše truth přímo

## 4.2 Research semantics zůstávají v research
- syntax
- deterministic transform
- formatter behavior
- fallback eligibility
- research epistemic rules

To vše zůstává v `jeff/cognitive/research/`.

## 4.3 Infrastructure zůstává technická
Infrastructure má vlastnit jen:
- routing
- runtime config
- strategies
- capabilities
- execution surface pro model calls

Ne:
- findings
- proposal semantics
- evaluation semantics
- governance semantics

## 4.4 No broad rewrite
Další práce budou bounded slices.
Ne velké přestavby.

## 4.5 Prompty jako kontrakty
Aktivní prompty musí být:
- file-backed
- reviewovatelné
- role-specific
- testované
- centrálně uložené v `PROMPTS/`

---

# 5. Doporučené pořadí další cesty

## Milestone 1 — Research reliability hardening -NOT DONE
Cíl:
udělat research dost robustní pro opakované reálné použití.

### Proč je to teď první
Research už funguje, ale live runs ukázaly, že Step 1 bounded output je ještě občas křehký.
To je lepší dorovnat teď než na tom stavět další cognitive vrstvu.

### Co sem patří
- doladění Step 1 promptů přes reálné fail cases
- stabilizace section compliance
- ladění sentinelů a epistemic wording
- opakované real-world terminal verification
- případně později úzké rozhodnutí o formatter eligibility pro konkrétní syntax fail cases

### Definition of done
- docs runs a web runs procházejí výrazně stabilněji než dnes
- Step 1 už není běžný bottleneck
- research je použitelný jako opora pro další vrstvu

---

## Milestone 2 — Proposal foundation
Cíl:
přidat první skutečnou vrstvu mezi research a autonomní rozhodování.

### Co má Proposal v1 dělat
Proposal vrstva má umět:
- vzít context + optional research outputs
- navrhnout 0–3 realistické možnosti
- každou možnost strukturovat
- uvést proč dává smysl
- uvést rizika / open questions
- nepředstírat permission ani final decision

### Co má zůstat mimo Proposal
- selection
- approval
- execution
- truth mutation

### Doporučený tvar Proposal v1
#### Step P1 — proposal generation
- bounded text nebo jiný přísný contract
- model-backed přes `ContractRuntime`

#### Step P2 — proposal normalization
- deterministic parse nebo formatter path podle potřeby

#### Step P3 — proposal validation
- fail-closed shape validation
- no invented action authority

### Definition of done
- Proposal umí vrátit použitelné bounded options
- návrhy jsou testované
- vrstva je runtime-wired přes existující Infrastructure

---

## Milestone 3 — Selection and Evaluation hardening
Cíl:
přestat být jen ve fázi „máme návrhy“, a dostat se k bounded rozhodovací smyčce.

### Selection v1
Selection má umět:
- vybrat jednu proposal variantu
- nebo vrátit reject / defer / escalate
- nepřidělovat permission
- nezaměňovat selection za governance

### Evaluation v1
Evaluation má umět:
- posoudit execution outcome
- určit:
  - success
  - mismatch
  - retry candidate
  - revalidate needed
  - terminate
  - escalate

### Definition of done
- proposal output není slepá větev
- selection a evaluation mají jasné contracty
- rozhodovací backbone začíná být skutečný

---

## Milestone 4 — Action / Governance integration
Cíl:
propojit vybraný návrh s controlled execution path.

### Co sem patří
- action creation z selected proposal
- readiness checks
- approval boundary
- execution entry
- outcome capture

### Co sem nepatří
- nekontrolovaná autonomie
- “agent si rozhodne sám o všem”

### Definition of done
- selected work může legálně projít do governed execution
- governance je skutečně load-bearing, ne jen dekorace

---

## Milestone 5 — Durable state
Cíl:
pravda musí přežít restart.

### Potřebná rozhodnutí
Nejdřív explicitně rozhodnout:
- snapshot only
- snapshot + append-only transition log

Doporučený směr:
- file-backed snapshots
- append-only transition log

### Co sem patří
- save/load `GlobalState`
- versioning
- startup reload
- replay-safe transition model

### Definition of done
- Jeff po restartu neztrácí truth state

---

## Milestone 6 — Durable memory
Cíl:
continuity přes čas bez zaměnění memory za truth.

### Co sem patří
- durable memory store
- retrieval
- write discipline
- linking
- persistence oddělená od truth state

### Definition of done
- memory přežije restart
- memory dál zůstává jen support/continuity layer

---

## Milestone 7 — Production orchestrator flows
Cíl:
orchestrator má přestat být primárně testovací kostra a dostat reálné handler sety.

### Co sem patří
- production-grade handler maps
- bounded research/proposal/action flows
- handoff validation nad real outputs
- stop / hold / escalate behavior nad reálnými stage results

### Definition of done
- aspoň jeden skutečný flow běží přes orchestrator mimo testy

---

## Milestone 8 — Bounded continuation
Cíl:
Jeff umí pokračovat ve více krocích nebo více rune ch bez skrytého chaosu.

### Co sem patří
- continuation policy
- lawful resume
- explicit stop points
- operator-visible continuation state

### Definition of done
- Jeff umí omezeně pokračovat přes více kroků bez ztráty truthfulness

---

# 6. Praktické doporučené pořadí implementace

## Krátká verze

1. Research reliability hardening
2. Proposal foundation
3. Selection + Evaluation hardening
4. Action / Governance integration
5. Durable state
6. Durable memory
7. Production orchestrator flows
8. Bounded continuation

---

# 7. Co teď rozhodně nedělat

## 7.1 Neotevírat broad rewrites
Ne:
- přepis celé infrastructure
- přepis celého orchestratoru
- přepis CLI jen pro čistotu

## 7.2 Nezačínat novou vertikálu na křehkém researchu
Proposal nedává smysl, pokud live research padá na běžných use-casech příliš často.

## 7.3 Neřešit všechno přes prompty
Prompt pomůže.
Ale:
- parser
- validators
- transitions
- governance
- routing
mají zůstat mimo prompt.

## 7.4 Nepouštět se zatím do “full autonomy”
Bez durable truth, governance a evaluation je to falešná autonomie.

---

# 8. Co je nejbližší další krok

## Doporučený immediate next step
**Research live-reliability slice**

Konkrétně:
- ověřit Step 1 prompt po posledních úpravách na reálných docs/web příkladech
- případně doladit wording a canonical examples
- zapsat failure taxonomy pro Step 1 real-run failures
- potvrdit, že docs + web runs už běží rozumně stabilně

Teprve potom:
**Proposal foundation v1**

---

# 9. Definition of done pro “ready for autonomy progression”

Jeff je připravený jít od research směrem k bounded autonomii, když platí:

- research je spolehlivý v live runs
- proposal vrstva existuje a je usable
- selection a evaluation mají jasné outputs
- governance opravdu rozhoduje o execution path
- truth state je durable
- memory je durable a oddělená od truth
- orchestrator umí reálné flows
- interface pravdivě ukazuje stav a rozhodnutí

---

# 10. Závěr

Dnešní Jeff je:
- disciplinovaný
- architektonicky čistší než většina agent systémů
- ale stále jen v první skutečně živé modelové vertikále

To je dobrá pozice.

Správná cesta dál není:
- přidávat další “chytré” vrstvy bez pořadí
- nebo honit pseudo-autonomii

Správná cesta je:
- nejdřív zpevnit research
- potom postavit proposal
- potom vybudovat skutečný decision/execution backbone
- a až potom řešit autonomii přes čas
