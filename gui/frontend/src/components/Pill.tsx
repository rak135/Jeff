import { ButtonHTMLAttributes, ReactNode } from 'react';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  tone?: 'default' | 'accent' | 'approved' | 'blocked' | 'pending';
  children: ReactNode;
}

const TONE = {
  default: { active: 'bg-muted text-panel border-muted', idle: 'text-muted border-border hover:border-border-strong' },
  accent: { active: 'bg-accent text-[#1a1816] border-accent', idle: 'text-accent border-accent/40 hover:border-accent' },
  approved: { active: 'bg-approved text-white border-approved', idle: 'text-approved border-approved/40' },
  blocked: { active: 'bg-blocked text-white border-blocked', idle: 'text-blocked border-blocked/40' },
  pending: { active: 'bg-pending text-[#1a1816] border-pending', idle: 'text-pending border-pending/40' },
} as const;

export function Pill({ active = false, tone = 'default', children, className = '', ...rest }: Props) {
  const s = TONE[tone];
  return (
    <button
      {...rest}
      className={`font-mono text-[10px] tracking-wide px-2.5 py-1 rounded-sm border transition-colors ${active ? s.active : s.idle} disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
    >
      {children}
    </button>
  );
}
