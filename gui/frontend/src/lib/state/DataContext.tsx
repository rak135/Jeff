import { createContext, useContext, useMemo, useState, ReactNode, useCallback } from 'react';
import { createMockAdapter } from '../adapters';
import type { JeffAdapter } from '../adapters';

interface DataCtx {
  adapter: JeffAdapter;
  /** Bumped after any mutation to force re-renders in consumers that read lists. */
  version: number;
  refresh: () => void;
}

const Ctx = createContext<DataCtx | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const [adapter] = useState(() => createMockAdapter());
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion(v => v + 1), []);
  const value = useMemo(() => ({ adapter, version, refresh }), [adapter, version, refresh]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useData() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useData outside DataProvider');
  return v;
}
