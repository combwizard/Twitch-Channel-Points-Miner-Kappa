/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        twitch: {
          purple: "#9146ff",
          dark: "#0e0e10",
          panel: "#18181b",
          border: "#2f2f35",
          muted: "#adadb8",
        },
      },
    },
  },
  plugins: [],
};
