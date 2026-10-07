import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Causora — Decision Twin",
  description: "Day 1 decision-intelligence prototype with traceable mock evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
