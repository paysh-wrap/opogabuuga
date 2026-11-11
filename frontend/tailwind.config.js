/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gold: "#D4AF37",
        goldLight: "#F2D27A",
        blue: "#3B82F6",
        blueLight: "#93C5FD",
        bg: "#0A1020",
        card: "#111A33",
        border: "#1E2A4A",
        mandatory: "#FFC93C",
      },
    },
  },
  plugins: [],
};
