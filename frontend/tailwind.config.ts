import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        primary: {
          DEFAULT: "var(--color-primary)",
          foreground: "var(--color-primary-foreground)",
          hover: "var(--color-background-primary-hover)",
          light: "var(--color-background-light-primary)",
          disable: "var(--color-background-primary-disable)",
        },
        secondary: {
          DEFAULT: "var(--color-secondary)",
          foreground: "var(--color-secondary-foreground)",
        },
        tertiary: {
          DEFAULT: "var(--color-tertiary)",
          foreground: "var(--color-tertiary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--color-destructive)",
          foreground: "var(--color-destructive-foreground)",
          light: "var(--color-background-light-negative)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          foreground: "var(--color-accent-foreground)",
        },
        muted: {
          DEFAULT: "var(--color-muted)",
          foreground: "var(--color-muted-foreground)",
        },
        border: {
          DEFAULT: "var(--color-border)",
          strong: "var(--color-border-strong)",
          dark: "var(--color-border-dark)",
          selected: "var(--color-border-selected)",
          positive: "var(--color-border-positive)",
          warning: "var(--color-border-warning)",
          negative: "var(--color-border-negative)",
        },
        positive: {
          DEFAULT: "var(--color-content-positive)",
          light: "var(--color-background-light-primary)",
          secondary: "var(--color-content-positive-secondary)",
        },
        warning: {
          DEFAULT: "var(--color-content-warning)",
          light: "var(--color-background-light-warning)",
          secondary: "var(--color-content-warning-secondary)",
        },
        dark: {
          DEFAULT: "var(--color-dark)",
          secondary: "var(--color-dark-secondary)",
          tertiary: "var(--color-dark-tertiary)",
        },
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
      },
    },
  },
  plugins: [],
} satisfies Config;
