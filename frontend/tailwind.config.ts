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
        // Authority Font (Serif) - Headers, Case Titles, Legal Citations
        serif: ['Merriweather', 'Georgia', 'Times New Roman', 'serif'],
        display: ['Merriweather', 'Georgia', 'Times New Roman', 'serif'],
        // Utility Font (Sans) - UI Labels, Navigation, Buttons
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Arial', 'sans-serif'],
        // Data Font (Mono) - Dates, Case Numbers, Statutes
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // ============================================
        // THE "PAPER & STEEL" PALETTE
        // ============================================

        // The Canvas (Backgrounds)
        steel: '#F2F2F2',           // App Chrome - Neutral Grey
        paper: '#FFFCF9',           // Data Surfaces - Warm White
        canvas: '#ECE9D8',          // Classic Windows warm grey (USER SELECTED)

        // The Ink (Typography)
        ink: {
          DEFAULT: '#111111',       // Primary Text - Near Black
          secondary: '#555555',     // Secondary Text - Graphite
          muted: '#888888',         // Muted text
        },

        // Accent Colors
        navy: {
          DEFAULT: '#0A2540',       // The "Firm" color - Headers/Primary Buttons
          light: '#1a3a5c',         // Hover state
          dark: '#061829',          // Active/pressed state
        },
        alert: '#B91C1C',           // Critical deadlines - deeply saturated
        amber: '#D97706',           // Warnings - Court Amber

        // Status Colors (muted, professional)
        status: {
          critical: '#B91C1C',
          warning: '#D97706',
          success: '#15803D',
          info: '#0A2540',
          pending: '#6B7280',
        },

        // Legacy surface colors (for compatibility)
        surface: {
          DEFAULT: '#ECE9D8',
          light: '#F2F2F2',
          panel: '#FFFFFF',
          dark: '#D4D0C8',
        },

        // Grid colors for data tables
        grid: {
          line: '#E5E5E5',
          header: '#F5F5F5',
          zebra: '#F9FAFB',
        },

        // Terminal colors for AI dock
        terminal: {
          bg: '#1E1E1E',
          green: '#10B981',
          amber: '#F59E0B',
          text: '#D4D4D4',
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
