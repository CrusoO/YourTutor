import type { ReactNode } from "react";
import "./globals.css";
import AppFrame from "@/components/AppFrame";

export const metadata = {
  title: "YourTutor",
  description: "Student practice player",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}
