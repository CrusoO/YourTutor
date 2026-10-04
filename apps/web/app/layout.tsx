import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "YourTutor",
  description: "Student practice player",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="phone">{children}</div>
      </body>
    </html>
  );
}
