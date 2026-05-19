import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Photo Organizer v1",
  description: "Photo Organizer workbench for photo review, face review, and detail inspection"
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
