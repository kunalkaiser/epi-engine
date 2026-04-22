import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "EPI Engine",
  description: "Healthcare epidemiology decision-support platform",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
