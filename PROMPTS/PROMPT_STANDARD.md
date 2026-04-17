# PROMPT_STANDARD.md

## Účel

Tento dokument definuje jednotný standard pro psaní promptů v Jeffovi.

Cíle:

- držet prompty krátké, tvrdé a role-specific
- oddělit sémantiku od mechaniky
- snížit prompt chaos mezi moduly
- zlepšit spolehlivost, review a evaly
- zabránit tomu, aby prompt nahrazoval architekturu

Prompt není architektura.
Prompt není parser.
Prompt není provenance validator.
Prompt není fallback policy engine.

Prompt má dělat jen to, co je skutečně práce modelu.

---

## Základní principy

### 1. Jedna role, jeden úkol

Každý prompt musí odpovídat jedné konkrétní roli.

Správně:
- Research Step 1 synthesis
- Research Step 3 formatter
- Proposal generation
- Evaluation judgment

Špatně:
- jeden univerzální prompt pro celý modul
- jeden prompt, který zároveň analyzuje, formátuje, validuje a rozhoduje fallback

---

### 2. Poctivost je důležitější než plynulost

Jeff preferuje:

- užší podložený výstup
- explicitní nejistotu
- odmítnutí doplnit nepodložený obsah

před:

- hezky znějícím textem
- “helpful” doplňováním
- skrytou improvizací

---

### 3. Prompt musí být explicitní

Prompt nesmí spoléhat na to, že model „pochopí záměr“.

Musí explicitně říct:

- co je role modelu
- co jsou vstupy
- co je povolené
- co je zakázané
- jak má vypadat výstup
- co dělat, když informace chybí

---

### 4. Missing-information behavior je povinný

Každý prompt musí obsahovat pravidla pro situace, kdy:

- evidence nestačí
- sekce nemá přirozený obsah
- není možné tvrdit nic silnějšího
- model neidentifikuje explicitní nejistotu

Model nesmí tyto situace řešit improvizací.

---

### 5. Prompt nesmí nést systémovou logiku

Prompt nemá vlastnit:

- parser pravidla, která mohou být deterministická
- provenance validaci
- routing
- persistence
- state transitions
- business logic mimo konkrétní modelový krok

Všechno, co jde fail-closed deterministicky, má být mimo prompt.

---

### 6. Jeden canonical example je lepší než dlouhá omáčka

Každý důležitý prompt má mít:

- jeden krátký validní příklad
- přesně ve tvaru, který očekáváme

Ne:
- pět variant
- dlouhé vysvětlování
- “inspirativní” ukázky

---

## Povinná struktura promptu

Každý prompt v Jeffovi má mít těchto 7 bloků.

### 1. Role

Musí říct:

- kdo model je
- jaký je jeho úkol
- co není jeho úkol

Příklad:
- You are Step 1 research synthesis.
- Your job is to synthesize bounded content from the provided evidence only.
- You do not normalize final JSON, invent citations, or decide persistence.

---

### 2. Inputs

Musí říct:

- co model dostává
- v jakém tvaru
- co smí brát jako zdroj pravdy

Příklad:
- question
- evidence pack
- allowed citation keys
- output syntax contract

---

### 3. Output contract

Musí říct:

- co má model vrátit
- v jakém formátu
- co je povinné
- co je přesná syntax

Příklad:
- exact section order
- exact bullet syntax
- exact sentinel values

---

### 4. Forbidden behavior

Musí explicitně zakázat:

- inventing findings
- inventing citations
- omitting required sections
- overstating certainty
- returning the wrong format

---

### 5. Missing-information behavior

Musí explicitně říct:

- co dělat, když není co vyplnit
- co dělat, když evidence nestačí
- co dělat, když nejistota není explicitně identifikovaná

Příklad:
- If no explicit uncertainties are identified from the provided evidence, emit exactly:
  `- No explicit uncertainties identified from the provided evidence.`

---

### 6. Epistemic rules

Musí explicitně říct:

- jak rozlišovat finding vs inference vs uncertainty
- že model nesmí tvrdit víc, než evidence unese
- že má být raději užší a přesnější než širší a spekulativní

---

### 7. Canonical example

Jeden krátký validní příklad.
Ne víc.

---

## Povinné typy instrukcí

Každý Jeff prompt musí obsahovat tyto 4 typy instrukcí.

### A. Scope instructions

Vymezují, co model smí použít.

Například:
- use only the provided evidence
- use only the allowed citation keys
- do not use outside knowledge

---

### B. Shape instructions

Vymezují přesný tvar výstupu.

Například:
- exact section order
- exact bullet syntax
- exact field names
- exact sentinel forms

---

### C. Epistemic instructions

Vymezují, jak má model zacházet s jistotou a podporou.

Například:
- distinguish findings from inferences
- do not claim certainty beyond the evidence
- do not smooth contradictions away

---

### D. Missing-information instructions

Vymezují, co dělat, když nějaký obsah chybí.

Například:
- emit required sentinel bullet
- keep the section present
- do not leave the section empty
- do not invent content to fill the gap

---

## Anti-goals

Každý prompt musí mít i anti-goals.
Tedy ne jen co má dělat, ale i co dělat nesmí.

Příklady anti-goals:

- do not be helpful by adding unsupported content
- do not guess missing claims
- do not hide uncertainty with fluent language
- do not merge separate epistemic categories into one blob
- do not improve weak evidence by reinterpretation

---

## Prompt psací pravidla

### Rule 1
Prompt musí být co nejkratší, ale pořád explicitní.

### Rule 2
Jedna role, jeden výstupní kontrakt.

### Rule 3
Každá povinná sekce nebo pole musí být jmenována explicitně.

### Rule 4
Každý prompt musí obsahovat missing-information behavior.

### Rule 5
Každý důležitý prompt má mít jeden canonical example.

### Rule 6
Zakázaná chování musí být napsaná natvrdo.

### Rule 7
Prompt nesmí přebírat odpovědnost za deterministickou validaci.

### Rule 8
Prompt musí být reviewovatelný jako kontrakt, ne jako volná esej.

---

## Naming conventions

### Prompt names

Prompty pojmenovávat podle role, ne podle modulu obecně.

Správně:
- `RESEARCH_STEP1_SYNTHESIS_PROMPT`
- `RESEARCH_STEP3_FORMATTER_PROMPT`
- `PROPOSAL_GENERATION_PROMPT`
- `EVALUATION_JUDGMENT_PROMPT`

Špatně:
- `MAIN_RESEARCH_PROMPT`
- `GENERAL_AGENT_PROMPT`
- `UNIVERSAL_STRUCTURED_OUTPUT_PROMPT`

---

## Template

```text
ROLE
You are <specific role>. Your job is to <specific job>. You do not <anti-job 1>, <anti-job 2>.

INPUTS
You will receive:
- <input 1>
- <input 2>
- <input 3>

Use only these inputs as evidence/truth.

OUTPUT CONTRACT
Return exactly:
- <required structure>
- <required section order>
- <required syntax>

FORBIDDEN
- Do not <forbidden behavior 1>
- Do not <forbidden behavior 2>
- Do not <forbidden behavior 3>

WHEN INFORMATION IS MISSING
- If <missing case 1>, do <required fallback 1>
- If <missing case 2>, do <required fallback 2>

EPISTEMIC RULES
- Distinguish <type A> from <type B>
- Do not claim certainty beyond the evidence
- Prefer narrower supported claims over broader unsupported claims

CANONICAL EXAMPLE
<one short valid example>

FINAL RULE
If the evidence does not support stronger content, keep the answer narrower and more honest rather than guessing.
