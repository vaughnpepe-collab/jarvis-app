import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        verra: {
          black:     "#0A0A0A",
          charcoal:  "#1B1B1B",
          ivory:     "#F8F7F4",
          gold:      "#D4AF37",
          "gold-light": "#E8C84A",
          "gold-dark":  "#B8962E",
          ash:       "#888884",
          smoke:     "#3A3A3A",
        },
      },
      fontFamily: {
        serif:  ["var(--font-cormorant)", "Georgia", "serif"],
        sans:   ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      letterSpacing: {
        widest2: "0.25em",
        widest3: "0.35em",
      },
      animation: {
        "fade-in":        "fadeIn 1.2s ease forwards",
        "fade-up":        "fadeUp 1s ease forwards",
        "marquee":        "marquee 40s linear infinite",
        "slow-zoom":      "slowZoom 20s ease-in-out infinite alternate",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeUp: {
          "0%":   { opacity: "0", transform: "translateY(40px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: {
          "0%":   { transform: "translateX(0%)" },
          "100%": { transform: "translateX(-50%)" },
        },
        slowZoom: {
          "0%":   { transform: "scale(1)" },
          "100%": { transform: "scale(1.08)" },
        },
      },
      transitionTimingFunction: {
        luxury: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
