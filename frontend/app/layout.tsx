import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Order Payment Device",
  description: "Device unlock order and payment console"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
