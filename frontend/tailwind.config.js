/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Fonds — bleu nuit profond
        app: "#0B1220",
        surface: "#151F35",
        elevated: "#1D2A45",
        line: "#2A3A5C",
        // Principal (vert terrain) & accent (doré)
        primary: {
          DEFAULT: "#22A85A",
          light: "#2CC169",
          dark: "#16824A",
        },
        accent: {
          DEFAULT: "#F2B03D",
          light: "#F6C863",
          dark: "#E0952A",
        },
        // Texte & états
        ink: {
          DEFAULT: "#F5F6F8",
          body: "#E3E7EE",
          secondary: "#9AA4B8",
          muted: "#5E6982",
        },
        success: "#35C46A",
        danger: "#E05B52",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
