/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        inst: {
          50: "#ebf6ef",
          100: "#d2ecdb",
          200: "#a6d8b7",
          500: "#1e8a4c",
          600: "#007a35",
          700: "#006B2E",
          800: "#005424",
          900: "#003d1a",
        },
        oro: { 400: "#d4a72c", 500: "#b8901f" },
      },
      fontFamily: { sans: ["Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"] },
    },
  },
  plugins: [],
};
