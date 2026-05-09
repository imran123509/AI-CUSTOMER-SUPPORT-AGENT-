import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Montserrat", "sans-serif"],
        body: ["Trebuchet MS", "Segoe UI Symbol", "sans-serif"],
        accent: ["Nunito", "sans-serif"],
      },
      colors: {
        brand: {
          DEFAULT: "#5B5BD6",
          50: "#EEF0FF",
          500: "#5B5BD6",
          700: "#3F3FB0",
          900: "#1F1F66",
        },
      },
    },
  },
  plugins: [],
};

export default config;
