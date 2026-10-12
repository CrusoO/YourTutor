import type { ReactNode } from "react";
import "./globals.css";
import AppFrame from "@/components/AppFrame";
import FontLoader from "@/components/FontLoader";
import { COMFORT_INIT_SCRIPT } from "@/lib/comfort";

export const metadata = {
  title: "YourTutor",
  description: "Student practice player",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: COMFORT_INIT_SCRIPT }} />
      </head>
      <body>
        <FontLoader />
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}
