/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary:  '#00e5ff',
        surface:  '#070d14',
        base:     '#050a0f',
        border:   '#0d2035',
        muted:    '#3a5a7a',
      },
      fontFamily: {
        rajdhani: ['Rajdhani', 'sans-serif'],
        mono: ['Share Tech Mono', 'monospace'],
        exo: ['Exo 2', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
