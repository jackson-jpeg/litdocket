import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Georgia', 'Times New Roman', 'Times', 'serif'],
        display: ['Georgia', 'Times New Roman', 'Times', 'serif'],
        mono: ['IBM Plex Mono', 'Consolas', 'Monaco', 'monospace'],
      },
      colors: {
        // Enterprise IBM-style blue palette
        enterprise: {
          blue: {
            50: '#e8f1ff',
            100: '#d0e2ff',
            200: '#a6c8ff',
            300: '#78a9ff',
            400: '#4589ff',
            500: '#0f62fe',  // IBM Blue primary
            600: '#0043ce',
            700: '#002d9c',
            800: '#001d6c',
            900: '#001141',
          },
          // Cool grey scale
          grey: {
            50: '#f4f4f4',
            100: '#e0e0e0',
            200: '#c6c6c6',
            300: '#a8a8a8',
            400: '#8d8d8d',
            500: '#6f6f6f',
            600: '#525252',
            700: '#393939',
            800: '#262626',
            900: '#161616',
          },
        },
        // Status colors - muted, professional
        status: {
          critical: '#da1e28',  // IBM Red
          warning: '#f1c21b',   // IBM Yellow
          success: '#198038',   // IBM Green
          info: '#0043ce',      // IBM Blue dark
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
    },
  },
  plugins: [],
};

export default config;
