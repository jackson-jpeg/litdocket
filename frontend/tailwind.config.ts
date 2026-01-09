import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    // Override default border radius - ZERO RADIUS POLICY
    borderRadius: {
      'none': '0',
      'sm': '0',
      'DEFAULT': '0',
      'md': '0',
      'lg': '0',
      'xl': '0',
      '2xl': '0',
      '3xl': '0',
      'full': '0',
    },
    extend: {
      fontFamily: {
        // Serif for headings - authoritative, like court orders
        serif: ['Georgia', 'Times New Roman', 'Times', 'serif'],
        display: ['Merriweather', 'Georgia', 'Times New Roman', 'serif'],
        // System sans-serif for body/data
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Arial', 'sans-serif'],
        // Monospace for docket numbers, dates, data
        mono: ['IBM Plex Mono', 'Consolas', 'Monaco', 'monospace'],
      },
      colors: {
        // ============================================
        // LEGACY MODERN / UTILITARIAN AUTHORITY PALETTE
        // ============================================

        // Surface colors - "Enterprise Greys"
        surface: {
          DEFAULT: '#ECE9D8',  // Classic Windows warm grey
          light: '#F5F5F5',    // Alternative light surface
          panel: '#FFFFFF',    // Data entry areas only
          dark: '#D4D0C8',     // Windows 95 style
        },

        // Primary action - IBM/Navy Blue
        navy: {
          DEFAULT: '#000080',  // Classic Navy Blue
          deep: '#003366',     // IBM Deep Blue
          light: '#4169E1',    // Royal Blue for hover
          dark: '#00004d',     // Darker navy for active
        },

        // Status accents - MUTED, PROFESSIONAL
        filed: '#006400',      // Dark Green - for "Filed" status
        overdue: '#8B0000',    // Dark Red - for "Overdue" status

        // Enterprise color system (enhanced)
        enterprise: {
          blue: {
            50: '#e8f1ff',
            100: '#d0e2ff',
            200: '#a6c8ff',
            300: '#78a9ff',
            400: '#4589ff',
            500: '#0f62fe',    // IBM Blue primary
            600: '#0043ce',
            700: '#002d9c',
            800: '#001d6c',
            900: '#001141',
          },
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

        // Status colors - muted, professional (no neon)
        status: {
          critical: '#8B0000',   // Dark Red (was #da1e28)
          warning: '#B8860B',    // Dark Goldenrod (was #f1c21b)
          success: '#006400',    // Dark Green (was #198038)
          info: '#000080',       // Navy Blue (was #0043ce)
        },

        // Bevel border colors for 3D effects
        bevel: {
          light: '#FFFFFF',      // Top/left highlight
          dark: '#808080',       // Bottom/right shadow
          darker: '#404040',     // Deeper shadow
          highlight: '#DFDFDF',  // Subtle highlight
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      fontSize: {
        // Default to smaller, denser text
        'xxs': ['10px', { lineHeight: '14px' }],
        'xs': ['12px', { lineHeight: '16px' }],
        'sm': ['14px', { lineHeight: '20px' }],
      },
      boxShadow: {
        // No blur shadows - use borders instead
        'none': 'none',
        'inset': 'inset 0 0 0 1px',
      },
    },
  },
  plugins: [],
};

export default config;
