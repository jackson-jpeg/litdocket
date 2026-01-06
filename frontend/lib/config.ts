/**
 * Application configuration - centralized API URLs
 *
 * IMPORTANT: All components should import API_URL from this file
 * instead of using process.env.NEXT_PUBLIC_API_URL directly.
 * This ensures consistent fallback behavior in production.
 */

// Production API URL - must use HTTPS to avoid Mixed Content errors on HTTPS pages
const PRODUCTION_API_URL = 'https://litdocket-production.up.railway.app';

// Production WebSocket host (without protocol - protocol is determined at runtime)
const PRODUCTION_WS_HOST = 'litdocket-production.up.railway.app';

/**
 * Get the API base URL
 * Uses environment variable if set, falls back to production URL
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || PRODUCTION_API_URL;

/**
 * Get the WebSocket host
 * Uses environment variable if set, falls back to production host
 */
export const WS_HOST = process.env.NEXT_PUBLIC_WS_URL || PRODUCTION_WS_HOST;

/**
 * Check if we're in development mode
 */
export const IS_DEV = process.env.NODE_ENV === 'development';

/**
 * Log configuration on startup (only in dev)
 */
if (typeof window !== 'undefined' && IS_DEV) {
  console.log('[Config] API_URL:', API_URL);
  console.log('[Config] WS_HOST:', WS_HOST);
  console.log('[Config] Environment:', process.env.NODE_ENV);
}
