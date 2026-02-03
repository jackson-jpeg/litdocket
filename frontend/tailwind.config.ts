import type { Config } from "tailwindcss";
import colors from "tailwindcss/colors";

/**
 * PAPER & STEEL DESIGN SYSTEM
 * "Bloomberg Law meets Linear"
 * Professional, high-contrast, whitespace-heavy, trustworthy
 */

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ============================================
        // PAPER & STEEL SEMANTIC PALETTE
        // "Bloomberg Law meets Linear"
        // ============================================

        // Paper Colors - Light background foundation
        paper: {
          DEFAULT: '#FDFBF7',   // Warm off-white (aged paper)
          warm: '#FAF8F3',      // Slightly warmer
          pure: '#FFFFFF',      // Pure white for cards
        },

        // Surface Colors - Card/modal backgrounds
        surface: {
          DEFAULT: '#F5F2EB',   // Light tan surface
          elevated: '#FFFFFF',  // Elevated cards
          muted: '#F8FAFC',     // slate-50 alternative
        },

        // Steel Colors - Dark accents
        steel: {
          DEFAULT: '#2C3E50',   // Primary steel blue-grey
          dark: '#1A252F',      // Darker steel for sidebar
          light: '#34495E',     // Lighter steel for hover
        },

        // Wax Colors - Legal accent (deep red/burgundy)
        wax: {
          DEFAULT: '#8B0000',   // Dark red (wax seal)
          light: '#A52A2A',     // Brown-red
          dark: '#660000',      // Darker burgundy
        },

        // Ink Colors - Text hierarchy
        ink: {
          DEFAULT: '#1A1A1A',   // Primary text (near black)
          secondary: '#4A4A4A', // Secondary text
          muted: '#6B7280',     // Muted/disabled text
          subtle: '#9CA3AF',    // Subtle text
        },

        // Base Colors - Light Mode Foundation (legacy support)
        app: {
          bg: '#f8fafc',        // slate-50 - Main page background
          surface: '#ffffff',   // white - Cards/Modals
        },

        // Text Hierarchy
        text: {
          primary: '#0f172a',   // slate-900 - Primary text
          secondary: '#64748b', // slate-500 - Secondary text
          muted: '#94a3b8',     // slate-400 - Muted text
        },

        // Borders
        border: {
          subtle: '#e2e8f0',    // slate-200 - Subtle borders
          emphasis: '#cbd5e1',  // slate-300 - Emphasis borders
        },

        // Sidebar - Dark Slate
        sidebar: {
          bg: '#0f172a',        // slate-900 - Sidebar background
          text: '#cbd5e1',      // slate-300 - Sidebar text
          hover: '#1e293b',     // slate-800 - Hover state
          active: '#1e293b',    // slate-800 - Active state
        },

        // Priority Colors for Deadlines
        priority: {
          fatal: '#C0392B',     // Distinct red for fatal (different from critical)
          critical: '#D35400',  // Orange for critical
          important: '#E67E22', // Lighter orange/amber for important
          standard: '#3498DB',  // Blue for standard
          info: '#7F8C8D',      // Grey for informational
        },

        // Deadline display colors (explicit mapping)
        fatal: {
          DEFAULT: '#C0392B',
          light: '#FADBD8',
          border: '#E74C3C',
        },
        critical: {
          DEFAULT: '#D35400',
          light: '#FAE5D3',
          border: '#E67E22',
        },
        important: {
          DEFAULT: '#E67E22',
          light: '#FEF5E7',
          border: '#F39C12',
        },

        // Status Colors
        status: {
          success: '#16a34a',   // green-600
          warning: '#f59e0b',   // amber-500
          error: '#dc2626',     // red-600
          info: '#3b82f6',      // blue-500
        },

        // Overdue text color
        overdue: '#B91C1C',     // red-700 for overdue items

        // Enterprise grey (legacy)
        'enterprise-grey': {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827',
        },

        // Legacy compatibility (for gradual migration)
        navy: '#3b82f6',
        alert: '#dc2626',
        amber: colors.amber,
        success: '#16a34a',
      },

      fontFamily: {
        // Professional Typography Stack
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['SF Mono', 'Monaco', 'Consolas', 'monospace'],
      },

      fontSize: {
        'xxs': ['0.625rem', { lineHeight: '0.875rem' }],  // 10px
        'xs': ['0.75rem', { lineHeight: '1rem' }],         // 12px
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],     // 14px
        'base': ['0.875rem', { lineHeight: '1.5rem' }],    // 14px
        'lg': ['1rem', { lineHeight: '1.5rem' }],          // 16px
        'xl': ['1.125rem', { lineHeight: '1.75rem' }],     // 18px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],         // 24px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],    // 30px
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],      // 36px
      },

      boxShadow: {
        // Subtle shadows for light mode
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        'command': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
      },

      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },

      // Fixed viewport heights for fullscreen layout
      height: {
        'screen-minus-header': 'calc(100vh - 64px)',
      },
    },
  },
  plugins: [],
};

export default config;
