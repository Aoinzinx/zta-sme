// dashboard/app/layout.tsx

import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "ZT-SME Admin Dashboard",
  description: "Zero Trust Framework — Administrative Interface",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
