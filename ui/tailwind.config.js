const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  important: true,
  theme: {
    extend: {},
    fontFamily: {
      'mono': ['Fira Mono', ...defaultTheme.fontFamily.mono],
    },
  },
  plugins: [],
}
