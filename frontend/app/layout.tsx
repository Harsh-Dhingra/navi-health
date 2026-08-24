import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NAVI | Healthcare Navigation",
  description: "Your AI guide through the U.S. healthcare system.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
