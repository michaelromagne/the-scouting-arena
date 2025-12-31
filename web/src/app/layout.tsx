import type { Metadata } from "next";
import { Inter, Poppins } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import SessionProvider from "@/components/SessionProvider";
import { ToastProvider } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { GoogleAnalytics } from "@/components/GoogleAnalytics";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "The Scouting Arena - Advanced Football Analytics & Player Scouting",
  description: "Compare 5,000+ football players from top European leagues. Advanced analytics, rankings, head-to-head comparisons, and similarity search for Premier League, La Liga, Serie A, Bundesliga & more.",
  keywords: ["football analytics", "player rankings", "football comparison", "soccer analytics", "player similarity", "team analysis", "national team stats"],
  authors: [{ name: "The Scouting Arena" }],
  creator: "The Scouting Arena",
  publisher: "The Scouting Arena",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" },
    ],
    apple: "/favicon.svg",
  },
  openGraph: {
    title: "The Scouting Arena",
    description: "Advanced Football Analytics & Player Scouting Platform",
    type: "website",
    locale: "en_US",
    siteName: "The Scouting Arena",
  },
  twitter: {
    card: "summary",
    title: "The Scouting Arena",
    description: "Advanced Football Analytics & Player Scouting Platform",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <GoogleAnalytics measurementId={process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || ""} />
      </head>
      <body
        className={`${inter.variable} ${poppins.variable} font-sans antialiased flex flex-col min-h-screen`}
      >
        <SessionProvider>
          <QueryProvider>
            <ToastProvider>
              <Navigation />
              <main className="flex-1">
                {children}
              </main>
              <Footer />
              <Toaster />
              <FeedbackWidget />
            </ToastProvider>
          </QueryProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
