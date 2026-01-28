import '@/lib/polyfills';
import type { Metadata } from "next";
import { Playfair_Display, Space_Grotesk, Newsreader, JetBrains_Mono } from 'next/font/google';
import "./globals.css";
import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/lib/auth/auth-context";
import ErrorBoundary from "@/components/ErrorBoundary";

// ============================================================================
// PAPER & STEEL TYPOGRAPHY SYSTEM
// ============================================================================

// Authority Font - Editorial headings (page titles, section headers)
const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
  weight: ['400', '700', '900'],
});

// Data/UI Font - Precision UI (deadlines, case numbers, labels)
const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
  weight: ['400', '500', '600', '700'],
});

// Body Font - Long-form legal text
const newsreader = Newsreader({
  subsets: ['latin'],
  variable: '--font-newsreader',
  display: 'swap',
  weight: ['400', '600'],
});

// Mono Font - Data precision (dates, IDs, statutes)
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
  weight: ['400', '500', '600'],
});

export const metadata: Metadata = {
  title: "LitDocket - AI Legal Docketing",
  description: "AI-powered legal docketing and case management system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${spaceGrotesk.variable} ${newsreader.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // URL.parse polyfill - must run before PDF.js worker loads
              if (typeof URL !== 'undefined' && !URL.parse) {
                URL.parse = function(url, base) {
                  try {
                    return new URL(url, base);
                  } catch {
                    return null;
                  }
                };
              }
            `,
          }}
        />
      </head>
      <body className="font-sans antialiased bg-slate-50 text-slate-900">
        <ErrorBoundary>
          <AuthProvider>
            <ToastProvider>
              {children}
            </ToastProvider>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
