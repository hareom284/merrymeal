/** MerryMeal — design tokens extracted from prototype 01.html (shadcn/ui) */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ['"Playfair Display"', "Georgia", "serif"],
        mono: ['"Geist Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // Warm editorial neutrals (replaces stock stone/gray)
        warm: {
          50:  "#faf9f8",   // page background
          100: "#f5f4f1",   // card / soft surface
          200: "#e8e6e1",   // borders / dividers
          300: "#d6d2cb",   // muted strokes
          400: "#b5ad9f",
          500: "#827b6f",   // muted body text
          600: "#5d574e",
          700: "#403c36",
          800: "#2c2a28",   // primary text
          900: "#1a1917",
        },
        brand: {
          // Charity teal-green (matches prototype 01.html)
          green: {
            DEFAULT: "#0f766e",   // teal-700
            hover: "#115e59",     // teal-800
            soft: "#ccfbf1",      // teal-100
          },
          // Warm accent for CTAs that aren't primary
          orange: {
            DEFAULT: "#f97316",
            hover: "#ea580c",
            soft: "#ffedd5",
          },
        },
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        card: "0 1px 3px rgba(44, 42, 40, 0.04), 0 4px 12px rgba(44, 42, 40, 0.06)",
      },
    },
  },
  plugins: [],
};
