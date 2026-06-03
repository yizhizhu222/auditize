/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nexus: {
          bg: '#0D1117',
          panel: '#161B22',
          border: '#30363D',
          blue: '#0969DA',
          'blue-hover': '#0550AE',
          accent: '#2EA043',
          warning: '#D29922',
          danger: '#DA3633',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['SF Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}