import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "MERCURY · Persistent Incident Intelligence",
  description: "Incident response that remembers what happened before.",
  icons: { icon: "/favicon.png", shortcut: "/favicon.png", apple: "/favicon.png" },
  openGraph: { title: "MERCURY", description: "Memory changed this decision", images: ["/og.png"] },
  twitter: { card: "summary_large_image", title: "MERCURY", description: "Memory changed this decision", images: ["/og.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Providers>{children}</Providers></body></html>;
}
