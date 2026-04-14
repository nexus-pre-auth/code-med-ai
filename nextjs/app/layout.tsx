import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CodeMed — AI Revenue Cycle Intelligence',
  description: 'Prior auth automation, denial management, and AR acceleration for healthcare billing teams.',
  metadataBase: new URL('https://codemedgroup.com'),
  openGraph: {
    title: 'CodeMed — AI Revenue Cycle Intelligence for Healthcare',
    description: 'Prior auth automation, denial management, and AR acceleration — so your billing team stops chasing and starts closing.',
    url: 'https://codemedgroup.com',
    siteName: 'CodeMed',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* Background decoration */}
        <div className="bg-grid" aria-hidden="true" />
        <div className="orb-tl" aria-hidden="true" />
        <div className="orb-br" aria-hidden="true" />
        <div className="ghost-text" aria-hidden="true">CODEMED</div>
        {/* Corner watermarks */}
        <span className="corner-codes" style={{ top: 16, left: 16 }}>I10 / E11.9</span>
        <span className="corner-codes" style={{ top: 16, right: 16 }}>CPT 99213</span>
        <span className="corner-codes" style={{ bottom: 16, left: 16 }}>HCC-85 / V28</span>
        <span className="corner-codes" style={{ bottom: 16, right: 16 }}>CARC-97</span>
        {/* App content */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </div>
      </body>
    </html>
  )
}
