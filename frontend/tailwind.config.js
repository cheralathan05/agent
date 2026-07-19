/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: {
          50: '#f8fafc',
          100: '#1e1e2e',
          200: '#1a1a2e',
          300: '#16162a',
          400: '#121226',
          500: '#0e0e22',
        },
        accent: {
          50: '#eef2ff',
          100: '#818cf8',
          200: '#6366f1',
          300: '#4f46e5',
          400: '#4338ca',
          500: '#3730a3',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
