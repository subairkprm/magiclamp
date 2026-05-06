/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Surface tokens — mapped to CSS variables so the theme switcher (and
        // the future RTL/Arabic skin) can swap palettes without rebuilds.
        bg:        'rgb(var(--ml-bg) / <alpha-value>)',
        surface:   'rgb(var(--ml-surface) / <alpha-value>)',
        elevated:  'rgb(var(--ml-elevated) / <alpha-value>)',
        border:    'rgb(var(--ml-border) / <alpha-value>)',
        muted:     'rgb(var(--ml-muted) / <alpha-value>)',
        fg:        'rgb(var(--ml-fg) / <alpha-value>)',
        'fg-muted':'rgb(var(--ml-fg-muted) / <alpha-value>)',
        accent:    'rgb(var(--ml-accent) / <alpha-value>)',
        'accent-fg': 'rgb(var(--ml-accent-fg) / <alpha-value>)',
        danger:    'rgb(var(--ml-danger) / <alpha-value>)',
        success:   'rgb(var(--ml-success) / <alpha-value>)',
        warning:   'rgb(var(--ml-warning) / <alpha-value>)',
        // Existing brand palette retained for backward compatibility.
        brand: {
          50:  '#f0f4ff',
          100: '#dce6fd',
          200: '#b9ccfb',
          300: '#8aaaf7',
          400: '#6188f2',
          500: '#4166ec',
          600: '#2e4fe0',
          700: '#253ccc',
          800: '#2232a5',
          900: '#212e82',
          950: '#161d51',
        },
      },
      borderRadius: {
        token: 'var(--ml-radius)',
      },
      transitionDuration: {
        token: 'var(--ml-motion)',
      },
    },
  },
  plugins: [],
}

