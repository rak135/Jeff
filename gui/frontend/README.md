# jeff · frontend prototype

A real, runnable, clickable operator console for Jeff. Future-oriented — models
the GUI Jeff is evolving toward, not just what CLI surfaces exist today.

## Stack

- React 18 + TypeScript
- Vite (dev server + bundler)
- Tailwind CSS (theme via CSS variables — light/dark warm palette)
- React Router v6 (HashRouter, so it works from `file://` and static hosts)

## Install & run

```bash
cd gui/frontend
npm install
npm run dev
# open http://127.0.0.1:5173
```

Other scripts:

```bash
npm run build      # production bundle into dist/
npm run preview    # serve dist/ locally
npm run typecheck  # tsc --noEmit
```

## Desktop app (Windows)

The frontend is packaged as a native Windows desktop app using [Tauri 2](https://tauri.app/).
The desktop shell lives in `src-tauri/` and wraps the existing Vite frontend — no
UI changes, no second codebase. HashRouter already makes the SPA work from the
`tauri://localhost` asset protocol, so the packaged app loads the same mock /
future data as the web prototype.

### Prerequisites (first time only)

- **Rust stable toolchain** — install via https://rustup.rs (`rustup-init.exe`,
  pick the MSVC host). Tauri needs `cargo` on `PATH`.
- **MSVC build tools** — "Desktop development with C++" workload from Visual
  Studio / Build Tools.
- **WebView2 runtime** — preinstalled on Windows 11; on Windows 10 get the
  Evergreen runtime from Microsoft.

### Desktop dev mode

```bash
cd gui/frontend
npm install          # once
npm run desktop:dev  # launches Vite + opens the Jeff desktop window
```

This runs `tauri dev`, which starts the Vite dev server (configured via
`beforeDevCommand` in `src-tauri/tauri.conf.json`) and opens the app in a real
native window with hot-reload. No browser required.

### Build the Windows desktop app

```bash
cd gui/frontend
npm run desktop:build
```

This runs `npm run build` to produce `dist/`, then compiles the Rust shell and
bundles everything. Output lands in `src-tauri/target/release/`:

- Portable executable:
  `src-tauri/target/release/jeff-desktop.exe`
- MSI installer:
  `src-tauri/target/release/bundle/msi/Jeff_<version>_x64_en-US.msi`
- NSIS setup:
  `src-tauri/target/release/bundle/nsis/Jeff_<version>_x64-setup.exe`

Double-click the `.exe` to launch, or run either installer for a Start-menu
shortcut and uninstaller entry. The packaged app bundles the built `dist/`
assets — it does **not** require a dev server.

### Data in the packaged app

The packaged desktop app uses the same adapter seam as the web prototype, so it
still runs on the mock / future data set today. To wire in real Jeff backend
surfaces later, swap the adapter in `src/lib/state/DataContext.tsx` as
described in *Connecting real backend later* below; no changes to the desktop
shell are needed.

### Why Tauri (not Electron)

Tauri reuses Windows' built-in WebView2, so the installer is a few MB instead
of ~150 MB, startup is faster, and no Chromium is shipped with the app. The
existing Vite/React/Tailwind/HashRouter stack plugs in unchanged.

## Project structure

```
src/
  main.tsx              app entry (providers + router)
  App.tsx               route table
  index.css             tailwind + theme CSS variables
  layout/
    Shell.tsx           sidebar + topbar + outlet
    Sidebar.tsx         projects / work-units / runs navigation
    TopBar.tsx          scope breadcrumb, data-source badge, theme toggle
  pages/
    Overview.tsx        operator dashboard — attention, changes, health
    RunsList.tsx        cross-project run search & filter
    RunDetail.tsx       full run experience: lifecycle, trace, rationale, telemetry, related
    ChangesReview.tsx   change proposal list + detail with diff + approve/reject
    Health.tsx          health signal board (future-facing)
    Memory.tsx          memory candidates vs committed
    Lookup.tsx          global search across runs, changes, memory
    Settings.tsx        policy rules, provider mode, appearance
    NewRun.tsx          start a new run inside a work unit
    ProjectView.tsx     project + work-unit views
  components/
    LayerPanel.tsx      expandable 10-layer lifecycle cell
    Subcard.tsx         panel primitives
    Pill.tsx            button primitive
    StatusChip.tsx      status pill, dot, glyphs — preserves semantic distinctions
    TruthTag.tsx        canonical / support / derived / memory / UI-LOCAL tags
  lib/
    contracts/types.ts  domain contracts (Project, Run, LayerFrame, ChangeProposal, …)
    adapters/
      index.ts          JeffAdapter interface — the single insertion point for real backend
      mockAdapter.ts    in-memory mock implementation
    mocks/data.ts       seed data
    state/
      ThemeContext.tsx  light/dark via CSS variables
      DataContext.tsx   wraps the adapter + a bump-version refresh
```

## How mock / future data is organised

Everything the UI reads goes through `JeffAdapter` (`src/lib/adapters/index.ts`).
Today there is exactly one implementation — `createMockAdapter()` — which seeds
from `src/lib/mocks/data.ts` and mutates an in-memory store.

Data provenance is labelled in two axes:

- **Truth class** via `<TruthTag />`: `canonical`, `support`, `derived`,
  `memory`, `local`. These match the vocabulary Jeff uses (see
  `v1_doc/ARCHITECTURE.md`). The UI never collapses them.
- **Backing** via `<BackingTag />`: `real` (backed by an actual Jeff surface),
  `future` (designed surface, backend not yet wired), `mock` (the current
  default). Surfaces like *changes review*, *health telemetry*, and
  *memory candidates* are visibly marked `future · prototype`.

`Run.status` carries Jeff's honest statuses — `active`, `blocked`, `degraded`,
`inconclusive`, `deferred`, `escalated`, `stalled`, `done`, `pending`. The UI
renders each distinctly; nothing is flattened into "failed".

## Connecting real backend later

1. Implement `JeffAdapter` against real endpoints (e.g. an HTTP wrapper over
   `jeff/interface/json_views.py` output, or a websocket lifecycle stream).
2. Construct it in `src/lib/state/DataContext.tsx` in place of
   `createMockAdapter()` (or compose them for hybrid mode).
3. Keep contracts in `src/lib/contracts/types.ts` stable — extend optionally,
   don't break consumers.
4. Flip `meta.mode` to `hybrid` / `future-live-placeholder`. The top-bar
   data-source pill will update automatically.

The UI never reads mock data directly. It reads through the adapter seam.

## Semantic rules the UI honors

- **Selected ≠ permitted ≠ approved ≠ applied ≠ executed ≠ evaluated.**
  The lifecycle shows these as separate layers with their own states.
- **Memory ≠ canonical truth.** Memory has its own surface; canonical state
  may reference only committed memory IDs.
- **History ≠ current truth.** Lookup, run history, and traces are labeled
  `support` / `derived`.
- **Approved ≠ applied.** The approval banner and change detail both say so
  explicitly.
- **Blocked ≠ failed.** Blocked runs are an honest escalation surface, with
  read-only inspection still permitted.

## What is fully simulated

- Change proposals (`backing: future`) — no backend yet.
- Health signals (`backing: future`) — no backend yet.
- Memory candidates (`backing: future`) — conceptual prototype.
- The 10-layer lifecycle content is shaped from `v1_doc/ARCHITECTURE.md` and
  `jeff/cognitive/*` naming, but the per-layer output bodies are seeded mocks.
- `retryRun`, `revalidateContext`, `approveChange`, `createRun` mutate in
  memory only.

## What is aligned with current Jeff

- Project / work_unit / run hierarchy.
- Ten-layer lifecycle (context → transition).
- Truth-class vocabulary.
- Policy rule names (`mutate_canonical_spec`, `internet_research`,
  `external_tool_call`, `memory_commit`, `long_running_autonomy`).
- Honest-escalation framing for blocked runs.
