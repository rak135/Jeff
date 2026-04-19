import { useTheme } from '../lib/state/ThemeContext';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { TruthTag, BackingTag } from '../components/TruthTag';
import { Pill } from '../components/Pill';

export function Settings() {
  const { theme, setTheme } = useTheme();
  const { adapter } = useData();

  const rules: Array<[string, string, boolean]> = [
    ['mutate_canonical_spec', 'require_operator_approval · require_readiness', true],
    ['internet_research', 'auto · scoped to active project', true],
    ['external_tool_call', 'require_readiness · log trace', true],
    ['memory_commit', 'auto · require_evidence_link', true],
    ['long_running_autonomy', 'disabled · v1', false],
  ];

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[900px] mx-auto px-6 py-6 space-y-4">
        <div>
          <div className="label-mono mb-1">SETTINGS</div>
          <div className="text-[22px] text-text font-medium tracking-tight">policy, readiness & appearance</div>
        </div>

        <PanelCard title="POLICY · RULES" truth={<TruthTag kind="canonical" />}>
          <div className="divide-y divide-border">
            {rules.map(([rule, eff, on]) => (
              <div key={rule} className="flex items-center gap-3 px-4 py-3">
                <div className="w-[220px] flex-none font-mono text-[12px] text-text">{rule}</div>
                <div className="flex-1 font-mono text-[11px] text-muted">{eff}</div>
                <div className={`w-8 h-[18px] rounded-full relative ${on ? 'bg-approved' : 'bg-border'}`}>
                  <div className={`absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white transition-all ${on ? 'left-4' : 'left-[2px]'}`} />
                </div>
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard title="DATA SOURCE · PROVIDER" truth={<TruthTag kind="local" />}>
          <div className="p-4 space-y-2">
            <div className="font-mono text-[11px] text-muted">
              provider · <span className="text-text">{adapter.meta.mode}</span> · v{adapter.meta.version}
            </div>
            <div className="text-[12px] text-muted">
              Real Jeff backend integration is not yet wired. Adapter interface in
              <span className="font-mono text-accent"> src/lib/adapters/index.ts</span> is the single insertion point.
            </div>
            <div className="flex gap-1.5 pt-1">
              <Pill active tone="default">mock</Pill>
              <Pill disabled>hybrid (future)</Pill>
              <Pill disabled>live (future)</Pill>
            </div>
            <BackingTag backing="mock" />
          </div>
        </PanelCard>

        <PanelCard title="APPEARANCE" truth={<TruthTag kind="local" />}>
          <div className="p-4">
            <div className="font-mono text-[10px] text-muted mb-1.5">theme</div>
            <div className="flex gap-1.5">
              {(['light', 'dark'] as const).map(v => (
                <Pill key={v} active={theme === v} tone={theme === v ? 'accent' : 'default'} onClick={() => setTheme(v)}>{v}</Pill>
              ))}
            </div>
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
