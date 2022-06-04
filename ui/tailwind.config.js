const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  important: true,
  theme: {
    extend: {},
    fontFamily: {
      'mono': ['Inconsolata', ...defaultTheme.fontFamily.mono],
    },
  },
  plugins: [],
}
