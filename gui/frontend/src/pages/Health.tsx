import { useMemo } from 'react';
import { useData } from '../lib/state/DataContext';
import { PanelCard } from '../components/Subcard';
import { BackingTag } from '../components/TruthTag';
import { Dot } from '../components/StatusChip';

export function Health() {
  const { adapter, version } = useData();
  const health = useMemo(() => adapter.listHealth(), [adapter, version]);

  const buckets = {
    blocked: health.filter(h => h.severity === 'blocked'),
    degraded: health.filter(h => h.severity === 'degraded'),
    pending: health.filter(h => h.severity === 'pending'),
    ok: health.filter(h => h.severity === 'ok'),
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1200px] mx-auto px-6 py-6 space-y-4">
        <div className="flex items-end gap-3">
          <div>
            <div className="label-mono mb-1">HEALTH · TELEMETRY</div>
            <div className="text-[22px] text-text font-medium tracking-tight">signals across runtime</div>
            <div className="text-[13px] text-muted mt-1">
              Signals are <b className="text-text">support</b>, not canonical truth. They point at places that may need attention.
            </div>
          </div>
          <BackingTag backing="future" />
        </div>

        <div className="grid grid-cols-4 gap-2">
          {(['blocked', 'degraded', 'pending', 'ok'] as const).map(b => (
            <div key={b} className="border border-border bg-panel rounded-sm p-3">
              <div className="label-mono">{b}</div>
              <div
                className={`font-mono text-[28px] mt-1 ${
                  b === 'blocked' ? 'text-blocked' : b === 'degraded' ? 'text-degraded' : b === 'pending' ? 'text-pending' : 'text-approved'
                }`}
              >
                {buckets[b].length}
              </div>
            </div>
          ))}
        </div>

        <PanelCard title="SIGNALS">
          <div className="divide-y divide-border">
            {health.map(h => (
              <div key={h.id} className="px-4 py-3 flex items-start gap-3">
                <Dot status={h.severity === 'ok' ? 'done' : h.severity} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] text-text">{h.name}</span>
                    <span className="font-mono text-[10px] text-faint">{h.scope}</span>
                  </div>
                  <div className="text-[12px] text-muted mt-0.5">{h.detail}</div>
                </div>
                <BackingTag backing={h.backing} />
              </div>
            ))}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
