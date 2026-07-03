import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PathPilot - AI Route Planning',
  description: 'Smart route planning using natural language',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  )
}
