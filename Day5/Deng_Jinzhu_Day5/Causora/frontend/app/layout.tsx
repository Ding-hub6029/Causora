import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Causora — Decision Twin",
  description: "Causora decision intelligence with reviewed simulations, traceable evidence, and guarded Boardroom analysis.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
