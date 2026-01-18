import type { Config } from "tailwindcss";

/**
 * BLOOMBERG TERMINAL DESIGN SYSTEM
 * "Maximum Density, Instant Clarity"
 * Dark theme optimized for long work sessions with neon accent colors
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
        // BLOOMBERG TERMINAL DARK THEME
        // ============================================

        // Dark Foundation
        terminal: {
          bg: '#0A0E14',
          panel: '#14181F',
          elevated: '#1C2128',
          surface: '#161B22',
          text: '#E6EDF3',      // Light gray text
          green: '#26DE81',     // Success/ready green
          amber: '#FFA502',     // Warning/attention amber
        },

        // Text Hierarchy
        text: {
          primary: '#E6EDF3',
          secondary: '#8B949E',
          muted: '#57606A',
          inverse: '#0A0E14',
        },

        // Accent Colors - Neon on Dark for Urgency Signals
        accent: {
          critical: '#FF4757',
          warning: '#FFA502',
          success: '#26DE81',
          info: '#45AAF2',
          purple: '#A55EEA',
        },

        // Priority Color Scale (Fatality Levels)
        priority: {
          fatal: '#FF4757',        // Bright red
          critical: '#FF6B6B',     // Red-orange
          high: '#FFA502',         // Bright orange
          medium: '#FFD93D',       // Yellow
          low: '#45AAF2',          // Blue
          info: '#8B949E',         // Gray
        },

        // Grid & Structural Elements
        border: {
          subtle: '#30363D',
          emphasis: '#444C56',
        },

        // Legacy compatibility (for gradual migration)
        navy: '#45AAF2',
        alert: '#FF4757',
        amber: '#FFA502',
        success: '#26DE81',
      },

      fontFamily: {
        // Bloomberg Typography Stack
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        tight: ['Inter Tight', 'Inter', 'sans-serif'],
        mono: ['IBM Plex Mono', 'SF Mono', 'Monaco', 'Consolas', 'monospace'],
      },

      fontSize: {
        'xxs': ['10px', { lineHeight: '14px' }],
        'xs': ['11px', { lineHeight: '16px' }],
        'sm': ['13px', { lineHeight: '18px' }],
        'base': ['13px', { lineHeight: '20px' }],
        'lg': ['14px', { lineHeight: '22px' }],
        'xl': ['16px', { lineHeight: '24px' }],
        '2xl': ['20px', { lineHeight: '28px' }],
        '3xl': ['24px', { lineHeight: '32px' }],
        '4xl': ['32px', { lineHeight: '40px' }],
      },

      boxShadow: {
        // Glow effects for critical items
        'glow-critical': '0 0 16px rgba(255, 71, 87, 0.4)',
        'glow-warning': '0 0 16px rgba(255, 165, 2, 0.3)',
        'glow-info': '0 0 12px rgba(69, 170, 242, 0.2)',
        'glow-success': '0 0 12px rgba(38, 222, 129, 0.2)',
      },

      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
      },

      keyframes: {
        glow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },

      // Fixed viewport heights for fullscreen layout
      height: {
        'screen-minus-header': 'calc(100vh - 48px)',
        'screen-minus-header-terminal': 'calc(100vh - 48px - 40px)',
      },
    },
  },
  plugins: [],
};

export default config;
