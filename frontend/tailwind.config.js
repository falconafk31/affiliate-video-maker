/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['JetBrains Mono', 'monospace'],
        retro: ['VT323', 'monospace'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        retro: {
          bg: '#050505',
          black: '#111111',
          cyan: '#00FFFF',
          magenta: '#FF00FF',
          yellow: '#FFFF00',
          green: '#00FF00',
          border: '#333333',
        },
        brand: {
          400: '#00FFFF', // Cyan replacing primary bright
          500: '#00CCCC', // Darker cyan
          600: '#FF00FF', // Magenta replacing primary dark
        },
      },
      animation: {
        'spin-slow': 'spin 1.5s linear infinite',
        'fade-in': 'fadeIn 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
