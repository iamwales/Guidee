/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        guidee: {
          bg: "#0f0f12",
          surface: "#1a1a22",
          border: "#2a2a36",
          accent: "#6366f1",
          accentHover: "#818cf8",
          text: "#f4f4f5",
          muted: "#a1a1aa",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        overlay: "0 8px 32px rgba(0, 0, 0, 0.45)",
      },
    },
  },
  plugins: [],
};
