import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Florida Docketing Assistant",
  description: "AI-powered legal docketing and case management for Florida courts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
