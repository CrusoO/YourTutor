import type { ReactNode } from "react";
import "./globals.css";
import AppFrame from "@/components/AppFrame";
import { notoSansDevanagari } from "./fonts";
import { COMFORT_INIT_SCRIPT } from "@/lib/comfort";

export const metadata = {
  title: "YourTutor",
  description: "Student practice player",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={notoSansDevanagari.variable} data-audience="school" data-density="regular" data-mascot="on" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: COMFORT_INIT_SCRIPT }} />
      </head>
      <body>
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}
