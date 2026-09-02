import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
export const metadata: Metadata = { title: "NeedRadar — Find your next AI opportunity", description: "Discover market needs before you build." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="zh-CN"><body><SiteHeader />{children}</body></html>; }
