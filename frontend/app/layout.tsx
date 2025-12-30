import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { NavbarComponent } from "@/components/ui/NavbarComponent";
import { Spotlight } from "@/components/ui/spotlight-new"
import Footer from "@/components/footer";



const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RaAI",
  description: "Ai Self Improvement Coach",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
      <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <Spotlight />
      <NavbarComponent />
      
        {children}
      <Footer />
      </ThemeProvider>
      </body>
     
      
    </html>
  );
}
