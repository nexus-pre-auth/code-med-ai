'use client'

interface Props {
  calendlyUrl?: string
}

export default function CTACard({ calendlyUrl }: Props) {
  return (
    <div
      className="card card-accent fade-in"
      style={{
        padding: '20px 24px',
        maxWidth: 680,
        background: 'linear-gradient(135deg, rgba(0,212,160,0.06) 0%, var(--card) 70%)',
        borderColor: 'var(--green-border)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>
            See your ROI in 15 minutes
          </div>
          <div style={{ color: 'var(--gray-light)', fontSize: 13, lineHeight: 1.5 }}>
            Book a personalized demo — we&apos;ll model your revenue opportunity based on your payer mix and claim volume.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
          {calendlyUrl ? (
            <a
              href={calendlyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
              style={{ borderRadius: 8, padding: '9px 18px', fontSize: 13, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
            >
              Book Demo
            </a>
          ) : (
            <a
              href="https://codemedgroup.com/demo"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
              style={{ borderRadius: 8, padding: '9px 18px', fontSize: 13, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
            >
              Book Demo
            </a>
          )}
          <a
            href="/pricing"
            className="btn-ghost"
            style={{ borderRadius: 8, padding: '9px 18px', fontSize: 13, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
          >
            See Pricing
          </a>
        </div>
      </div>
    </div>
  )
}
