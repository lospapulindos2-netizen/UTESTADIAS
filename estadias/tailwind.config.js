/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        inst: {
          50: "#eef3fb",
          100: "#d9e3f5",
          200: "#b3c7eb",
          500: "#2f5597",
          600: "#22447f",
          700: "#1b3666",
          800: "#152a4f",
          900: "#0f1f3a",
        },
        oro: { 400: "#d4a72c", 500: "#b8901f" },
      },
      fontFamily: { sans: ["Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"] },
    },
  },
  plugins: [],
};
