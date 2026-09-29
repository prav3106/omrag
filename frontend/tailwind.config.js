/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          50: '#f7f8f8', 100: '#eeeff1', 200: '#d9dce0', 300: '#b8bdc5',
          400: '#8f97a3', 500: '#6d7684', 600: '#565e6b', 700: '#464c56',
          800: '#3c414a', 900: '#23272e', 950: '#15181d',
        },
        accent: {
          50: '#eef3ff', 100: '#dfe8ff', 200: '#c5d5ff', 300: '#a0b8ff',
          400: '#7a93fb', 500: '#5a6ff2', 600: '#3f4de6', 700: '#333dca',
          800: '#2c36a3', 900: '#2a3481',
        },
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto',
               'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,20,26,.04), 0 1px 3px rgba(16,20,26,.06)',
      },
      keyframes: {
        rise: { '0%': { opacity: 0, transform: 'translateY(4px)' },
                '100%': { opacity: 1, transform: 'translateY(0)' } },
      },
      animation: { rise: 'rise .18s ease-out both' },
    },
  },
  plugins: [],
}
