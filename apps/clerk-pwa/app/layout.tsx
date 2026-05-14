import type { Metadata, Viewport } from 'next';
import { Geist } from 'next/font/google';
import { Toaster } from '@aura/ui';
import './globals.css';

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' });

export const metadata: Metadata = {
  title: 'Aura ID — Capture',
  description: 'Hotel front-desk ID capture',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: 'Aura ID' },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  themeColor: '#ffffff',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={geist.variable}>
      <body className="min-h-dvh bg-background font-sans antialiased">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
