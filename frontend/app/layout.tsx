import '@/lib/polyfills';
import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/lib/auth/auth-context";
import ErrorBoundary from "@/components/ErrorBoundary";

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
    <html lang="en">
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
      <body>
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
