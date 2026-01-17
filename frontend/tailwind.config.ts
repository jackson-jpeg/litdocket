import type { Config } from "tailwindcss";

/**
 * SOVEREIGN DESIGN SYSTEM
 * "Density is Reliability" - Neo-Enterprise / Informational Brutalism
 */

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    // ZERO RADIUS POLICY - No exceptions
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
        // PAPER & STEEL TYPOGRAPHY STACK
        // Authority Font (Serif) - Headers, Case Titles, Legal Citations
        heading: ['var(--font-playfair)', 'Playfair Display', 'Georgia', 'serif'],
        serif: ['var(--font-newsreader)', 'Newsreader', 'Georgia', 'Times New Roman', 'serif'],
        // Data/UI Font - Deadlines, Case Numbers, Tables
        sans: ['var(--font-space-grotesk)', 'Space Grotesk', 'system-ui', 'sans-serif'],
        // Precision Font (Mono) - Dates, IDs, Statutes
        mono: ['var(--font-jetbrains)', 'JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // ============================================
        // PAPER & STEEL PALETTE (Editorial Legal Utility)
        // ============================================

        // The Canvas (Backgrounds)
        paper: '#FDFBF7',           // Warm paper background
        surface: '#F5F2EB',         // Card stock surface
        steel: '#2C3E50',           // Deep charcoal/steel primary
        wax: '#8B0000',             // Sealing-wax crimson accent

        // The Ink (Typography)
        ink: {
          DEFAULT: '#1A1A1A',       // Near black - hard borders
          secondary: '#4A4A4A',     // Secondary text
          muted: '#888888',         // Muted text
        },

        // Deadline Fatality Colors (High Contrast)
        fatal: '#C0392B',           // Fatal deadlines - dark crimson
        critical: '#D35400',        // Critical - burnt orange
        important: '#E67E22',       // Important - orange
        standard: '#2C3E50',        // Standard - steel
        informational: '#7F8C8D',   // Info - graphite

        // Status Colors (Restrained, authoritative)
        status: {
          fatal: '#C0392B',
          critical: '#D35400',
          important: '#E67E22',
          success: '#27AE60',
          pending: '#7F8C8D',
        },

        // Legacy compatibility (minimized)
        navy: {
          DEFAULT: '#2C3E50',
          light: '#34495E',
          dark: '#1A252F',
        },
        alert: '#C0392B',
        amber: '#D35400',

        // Grid colors for dense data tables
        grid: {
          line: '#1A1A1A',          // Hard black lines
          header: '#F5F2EB',        // Card stock
          zebra: '#FDFBF7',         // Paper
          dark: '#1A1A1A',          // Dark grid background
        },

        // Terminal colors
        terminal: {
          bg: '#1A1A1A',
          green: '#27AE60',
          amber: '#D35400',
          text: '#F5F2EB',
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      fontSize: {
        'xxs': ['10px', { lineHeight: '14px' }],
        'xs': ['11px', { lineHeight: '16px' }],
        'sm': ['13px', { lineHeight: '20px' }],
        'base': ['14px', { lineHeight: '22px' }],
      },
      boxShadow: {
        // Hard shadows only - no blur
        'none': 'none',
        'hard': '4px 4px 0px 0px #000000',
        'hard-sm': '2px 2px 0px 0px #000000',
        'hard-navy': '4px 4px 0px 0px #0A2540',
      },
      // Fixed viewport heights for cockpit layout
      height: {
        'screen-minus-header': 'calc(100vh - 48px)',
        'screen-minus-header-terminal': 'calc(100vh - 48px - 40px)',
      },
    },
  },
  plugins: [],
};

export default config;
