import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArpadBot Dashboard",
  description: "Discord bot configuration and embed builder",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
