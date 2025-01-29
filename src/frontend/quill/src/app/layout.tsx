'use client';

import { Inter } from 'next/font/google'
import './globals.css'
import { DocumentProvider } from '@/context/DocumentContext'
import { ChatProvider } from '@/context/ChatContext'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <DocumentProvider>
          <ChatProvider>
            {children}
          </ChatProvider>
        </DocumentProvider>
      </body>
    </html>
  )
}