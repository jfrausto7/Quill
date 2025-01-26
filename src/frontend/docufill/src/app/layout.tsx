'use client';

import { Inter } from 'next/font/google'
import './globals.css'
import { DocumentProvider } from '@/context/DocumentContext'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} dark:bg-gray-900`}>
        <DocumentProvider>
          {children}
        </DocumentProvider>
      </body>
    </html>
  )
}