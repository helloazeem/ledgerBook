/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",  // Scan all HTML files in templates folder
    "./static/src/**/*.js"    // In case you add JavaScript files later
  ],
  theme: {
    extend: {},
  },
  plugins: [],
} 