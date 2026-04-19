import { ReactNode } from 'react';

interface Props {
  label: string;
  tone?: string;
  kindTag?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
}

export function Subcard({ label, kindTag, right, children }: Props) {
  return (
    <div className="border border-border rounded-sm mb-2 overflow-hidden bg-panel">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-surface">
        <span className="font-mono text-[9px] tracking-[.15em] uppercase text-muted">{label}</span>
        {kindTag}
        <span className="ml-auto">{right}</span>
      </div>
      <div>{children}</div>
    </div>
  );
}

export function PanelCard({
  title,
  truth,
  right,
  children,
  className = '',
}: {
  title: string;
  truth?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`border border-border rounded-sm bg-panel ${className}`}>
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <span className="font-mono text-[10px] tracking-[.15em] uppercase text-muted">{title}</span>
        {truth}
        <span className="ml-auto">{right}</span>
      </div>
      <div>{children}</div>
    </div>
  );
}
