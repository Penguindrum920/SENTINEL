import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'monospace'],
      },
      colors: {
        terminal: {
          green: '#00ff41',
          red: '#ff0040',
          amber: '#ffb800',
          cyan: '#00bfff',
          purple: '#bf00ff',
          bg: '#000000',
          panel: '#0a0a0a',
          border: '#1a1a1a',
        },
      },
      animation: {
        blink: 'blink 1s infinite',
        slideDown: 'slideDown 0.3s ease-out',
      },
      keyframes: {
        blink: {
          '0%, 50%': { opacity: '1' },
          '51%, 100%': { opacity: '0.3' },
        },
        slideDown: {
          from: { transform: 'translateY(-100%)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
