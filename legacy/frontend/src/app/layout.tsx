import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DemestiChat - LCARS Interface',
  description: 'Star Trek TNG inspired AI chat interface',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Antonio:wght@700&display=swap" rel="stylesheet" />
      </head>
      <body className="font-antonio bg-black text-lcars-orange antialiased">
        {children}
      </body>
    </html>
  )
}
