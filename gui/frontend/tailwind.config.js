/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        panel: 'var(--panel)',
        rail: 'var(--rail)',
        border: 'var(--border)',
        'border-strong': 'var(--border-strong)',
        text: 'var(--text)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        approved: 'var(--approved)',
        blocked: 'var(--blocked)',
        pending: 'var(--pending)',
        degraded: 'var(--degraded)',
        canonical: 'var(--canonical)',
        support: 'var(--support)',
        derived: 'var(--derived)',
        memory: 'var(--memory)',
        accent: 'var(--accent)',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
