'use client'

import type { Document } from '@/lib/supabase'

interface Props {
  document: Document
}

const TYPE_LABELS: Record<Document['type'], string> = {
  appeal_letter: 'Appeal Letter',
  pa_package: 'PA Package',
  roi_report: 'ROI Report',
}

const TYPE_COLORS: Record<Document['type'], string> = {
  appeal_letter: 'var(--green)',
  pa_package: 'var(--purple)',
  roi_report: 'var(--gold)',
}

export default function DocumentCard({ document: doc }: Props) {
  const typeLabel = TYPE_LABELS[doc.type]
  const typeColor = TYPE_COLORS[doc.type]

  const date = new Date(doc.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <div className="card" style={{ padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
      <div style={{ flex: 1 }}>
        {/* Type badge */}
        <div
          style={{
            display: 'inline-block',
            fontSize: 10,
            fontWeight: 700,
            color: typeColor,
            background: `${typeColor}18`,
            border: `1px solid ${typeColor}30`,
            borderRadius: 20,
            padding: '2px 10px',
            marginBottom: 8,
            fontFamily: 'IBM Plex Mono, monospace',
            letterSpacing: '0.04em',
          }}
        >
          {typeLabel.toUpperCase()}
        </div>

        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{doc.title}</div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {doc.payer && (
            <span style={{ fontSize: 12, color: 'var(--gray-light)' }}>
              <span style={{ color: 'var(--gray)' }}>Payer:</span> {doc.payer}
            </span>
          )}
          {doc.drug && (
            <span style={{ fontSize: 12, color: 'var(--gray-light)' }}>
              <span style={{ color: 'var(--gray)' }}>Drug:</span> {doc.drug}
            </span>
          )}
          <span style={{ fontSize: 12, color: 'var(--gray)' }}>{date}</span>
        </div>
      </div>

      <div style={{ flexShrink: 0 }}>
        {doc.pdf_url ? (
          <a
            href={doc.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost"
            style={{
              borderRadius: 8,
              padding: '8px 16px',
              fontSize: 12,
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <span>↗</span> Open PDF
          </a>
        ) : (
          <span style={{ fontSize: 12, color: 'var(--gray)' }}>No PDF</span>
        )}
      </div>
    </div>
  )
}
