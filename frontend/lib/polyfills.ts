/**
 * Polyfills for browser APIs not yet supported by Next.js
 * See: https://github.com/vercel/next.js/issues/72914
 */

// Type declaration for URL.parse
declare global {
  interface URLConstructor {
    parse(url: string | URL, base?: string | URL): URL | null;
  }
}

// Polyfill URL.parse() for Safari < 18 and Next.js
if (typeof URL !== 'undefined' && !(URL as any).parse) {
  (URL as any).parse = function(url: string | URL, base?: string | URL): URL | null {
    try {
      return new URL(url, base);
    } catch {
      return null;
    }
  };
}

export {};
