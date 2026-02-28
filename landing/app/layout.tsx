import type { Metadata } from "next";
import { Inter } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Keepfa.st — Il tuo analista di retention AI",
  description:
    "Connetti PostHog e Stripe, chiedi in linguaggio semplice, ricevi risposte che ti dicono cosa fixare oggi. Direttamente dentro Cursor o Claude.",
  metadataBase: new URL("https://keepfa.st"),
  openGraph: {
    title: "Keepfa.st — Il tuo analista di retention AI",
    description:
      "Tu buildi. L'AI legge. Tu decidi. L'AI misura.",
    url: "https://keepfa.st",
    siteName: "Keepfa.st",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Keepfa.st — Il tuo analista di retention AI",
    description:
      "Tu buildi. L'AI legge. Tu decidi. L'AI misura.",
    creator: "@MicLau93",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it" className={`${inter.variable} ${geistMono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
