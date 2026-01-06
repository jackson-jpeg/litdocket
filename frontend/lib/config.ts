/**
 * Application configuration - centralized API URLs
 *
 * CRITICAL: This file ensures production always uses HTTPS production URLs.
 * Localhost URLs are NEVER allowed in production builds.
 */

// Production API URL - HTTPS required to avoid Mixed Content errors
const PRODUCTION_API_URL = 'https://litdocket-production.up.railway.app';
const PRODUCTION_WS_HOST = 'litdocket-production.up.railway.app';

/**
 * Determine if we're in a production environment
 * Check multiple signals to be certain
 */
const isProduction =
  process.env.NODE_ENV === 'production' ||
  (typeof window !== 'undefined' && window.location.hostname !== 'localhost');

/**
 * Validate and get API URL
 * In production: ALWAYS use production URL, never localhost
 * In development: Use env var or fallback to production
 */
function getApiUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;

  // In production, NEVER allow localhost - always use production URL
  if (isProduction) {
    if (!envUrl || envUrl.includes('localhost') || envUrl.includes('127.0.0.1') || envUrl.startsWith('http://')) {
      return PRODUCTION_API_URL;
    }
  }

  return envUrl || PRODUCTION_API_URL;
}

/**
 * Validate and get WebSocket host
 * In production: ALWAYS use production host, never localhost
 */
function getWsHost(): string {
  const envHost = process.env.NEXT_PUBLIC_WS_URL;

  // In production, NEVER allow localhost
  if (isProduction) {
    if (!envHost || envHost.includes('localhost') || envHost.includes('127.0.0.1')) {
      return PRODUCTION_WS_HOST;
    }
  }

  return envHost || PRODUCTION_WS_HOST;
}

// Export validated URLs
export const API_URL = getApiUrl();
export const WS_HOST = getWsHost();
export const IS_DEV = process.env.NODE_ENV === 'development';

// Runtime validation - log warnings if config seems wrong
if (typeof window !== 'undefined') {
  if (window.location.protocol === 'https:' && API_URL.startsWith('http://')) {
    console.error('[Config] CRITICAL: HTTP API URL on HTTPS page will cause Mixed Content errors');
    console.error('[Config] Forcing HTTPS production URL');
    // Force override at runtime for HTTPS pages
    (globalThis as any).__LITDOCKET_API_URL__ = PRODUCTION_API_URL;
  }

  if (IS_DEV) {
    console.log('[Config] API_URL:', API_URL);
    console.log('[Config] WS_HOST:', WS_HOST);
  }
}

// Export a getter that checks runtime override
export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined' && (globalThis as any).__LITDOCKET_API_URL__) {
    return (globalThis as any).__LITDOCKET_API_URL__;
  }
  return API_URL;
}
