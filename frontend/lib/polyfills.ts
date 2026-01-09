/**
 * Polyfills for browser APIs not yet supported by Next.js
 * See: https://github.com/vercel/next.js/issues/72914
 */

// Polyfill URL.parse() for Safari < 18 and Next.js
if (typeof URL !== 'undefined' && !URL.parse) {
  URL.parse = function(url: string | URL, base?: string | URL): URL | null {
    try {
      return new URL(url, base);
    } catch {
      return null;
    }
  };
}

export {};
