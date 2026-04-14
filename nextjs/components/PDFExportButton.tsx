'use client'

import { useState } from 'react'

interface Props {
  content: string
  title: string
  token: string
  sessionId?: string
  payer?: string
  drug?: string
}

export default function PDFExportButton({ content, title, token, sessionId, payer, drug }: Props) {
  const [loading, setLoading] = useState(false)
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState('')

  async function handleExport() {
    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/documents/pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content, title, sessionId, payer, drug }),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'PDF generation failed')

      setUrl(data.url)

      // Open in new tab
      window.open(data.url, '_blank')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate PDF')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fade-in" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary"
          style={{ borderRadius: 8, padding: '8px 16px', fontSize: 12, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}
        >
          <span>↗</span> Open PDF
        </a>
      ) : (
        <button
          onClick={handleExport}
          disabled={loading}
          className="btn-primary"
          style={{ borderRadius: 8, padding: '8px 16px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
        >
          {loading ? (
            <>
              <span className="spin" style={{ display: 'inline-block', width: 12, height: 12, border: '2px solid rgba(10,15,26,0.3)', borderTopColor: '#0A0F1A', borderRadius: '50%' }} />
              Generating PDF...
            </>
          ) : (
            <>
              <span>⬇</span> Export PDF
            </>
          )}
        </button>
      )}
      {error && (
        <span style={{ fontSize: 12, color: 'var(--red)' }}>{error}</span>
      )}
    </div>
  )
}
