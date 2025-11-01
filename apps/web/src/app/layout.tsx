import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'LaborLookers - Professional Services Platform',
  description: 'Connect with trusted professionals for all your service needs',
  keywords: ['contractors', 'professionals', 'services', 'laborlookers'],
  authors: [{ name: 'LaborLookers Team' }],
  creator: 'LaborLookers',
  publisher: 'LaborLookers',
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://laborlookers.com',
    title: 'LaborLookers - Professional Services Platform',
    description: 'Connect with trusted professionals for all your service needs',
    siteName: 'LaborLookers',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'LaborLookers - Professional Services Platform',
    description: 'Connect with trusted professionals for all your service needs',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {children}
      </body>
    </html>
  )
}