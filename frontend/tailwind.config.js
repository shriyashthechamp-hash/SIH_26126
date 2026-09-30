/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: '#080909',
        secondary: '#101313',
        panel: '#151918',
        'panel-hover': '#1b2120',
        'border-subtle': '#1c2221',
        'border-grid': '#252A29',
        'border-strong': '#38403e',
        primary: '#F1F0EA',
        muted: '#8E9594',
        dim: '#59605F',
        amber: {
          500: '#F5A623',
          400: '#ffb84d',
        },
        brand: '#F5A623',
        'system-green': '#39FF88',
        'system-red': '#FF4D4D',
        'data-cyan': '#54D6FF',
      },
      fontFamily: {
        sans: ['Space Grotesk', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
