'use client'

export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 fade-in">
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #00D4A0, #00B386)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          fontSize: 12,
          fontWeight: 700,
          color: '#0A0F1A',
        }}
      >
        C
      </div>
      <div className="bubble-bot" style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  )
}
