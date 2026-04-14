import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0A0F1A',
        surface: '#10151F',
        card: '#141B28',
        card2: '#192030',
        green: {
          DEFAULT: '#00D4A0',
          2: '#00B386',
        },
        gray: {
          DEFAULT: '#6B8299',
          light: '#9BAFC4',
        },
        gold: '#F6AD3C',
        danger: '#FC5A5A',
        purple: '#9B8AFB',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      borderColor: {
        DEFAULT: 'rgba(255,255,255,0.07)',
        subtle: 'rgba(255,255,255,0.04)',
        green: 'rgba(0,212,160,0.22)',
      },
      backgroundImage: {
        'green-glow': 'rgba(0,212,160,0.12)',
      },
    },
  },
  plugins: [],
}

export default config
