import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Photo Organizer v1",
  description: "Face cluster review screen for Photo Organizer v1"
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
