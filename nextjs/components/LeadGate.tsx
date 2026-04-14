'use client'

import { useState } from 'react'

const ROLES = [
  'Revenue Cycle Director',
  'Billing Manager',
  'Practice Administrator',
  'CFO / VP Finance',
  'Physician / Provider',
  'Coding Specialist',
  'Denial Management Specialist',
  'Other',
]

interface Props {
  token: string
  onComplete: (leadId: string, name: string) => void
}

export default function LeadGate({ token, onComplete }: Props) {
  const [name, setName] = useState('')
  const [org, setOrg] = useState('')
  const [role, setRole] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !org.trim() || !role) {
      setError('All fields are required.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/leads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: name.trim(), org: org.trim(), role }),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to save')

      onComplete(data.id, name.trim())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div
        className="card card-accent"
        style={{ width: '100%', maxWidth: 480, padding: 40 }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div
            style={{
              fontSize: 22,
              fontWeight: 900,
              color: 'var(--green)',
              letterSpacing: '0.08em',
              fontFamily: 'IBM Plex Mono, monospace',
            }}
          >
            CODEMED
          </div>
          <div style={{ color: 'var(--gray-light)', fontSize: 13, marginTop: 4 }}>
            AI Revenue Cycle Intelligence
          </div>
        </div>

        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, textAlign: 'center' }}>
          Welcome to CodeMed
        </h2>
        <p style={{ color: 'var(--gray-light)', fontSize: 13, textAlign: 'center', marginBottom: 28, lineHeight: 1.5 }}>
          Tell us a bit about yourself so we can tailor your experience.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6, fontWeight: 500 }}>
              Full Name
            </label>
            <input
              className="input-dark"
              type="text"
              placeholder="Jane Smith"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6, fontWeight: 500 }}>
              Organization
            </label>
            <input
              className="input-dark"
              type="text"
              placeholder="Acme Medical Group"
              value={org}
              onChange={(e) => setOrg(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6, fontWeight: 500 }}>
              Your Role
            </label>
            <select
              className="input-dark"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              required
              style={{ cursor: 'pointer' }}
            >
              <option value="">Select a role...</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <p style={{ color: 'var(--red)', fontSize: 13 }}>{error}</p>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ borderRadius: 8, padding: '12px 24px', fontSize: 14, marginTop: 4 }}
          >
            {loading ? 'Saving...' : 'Get Started'}
          </button>
        </form>

        {/* Trust row */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 20,
            marginTop: 24,
            paddingTop: 20,
            borderTop: '1px solid var(--border)',
          }}
        >
          {['HIPAA Aware', '94% PA Approval', '6.2h Turnaround'].map((item) => (
            <div key={item} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--green)', fontWeight: 600 }}>{item}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
