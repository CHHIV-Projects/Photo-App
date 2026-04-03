import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Photo Organizer v1",
  description: "Minimal frontend skeleton for Photo Organizer v1"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
