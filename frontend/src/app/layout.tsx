import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "AI Agent",
  description: "AI-powered customer support platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Nunito:wght@400;600&display=swap"
        />
      </head>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
