'use client'

import { useState } from 'react'
import type { TierKey } from '@/lib/stripe'

const TIERS = [
  {
    key: 'starter' as TierKey,
    name: 'Starter',
    price: '$2,500',
    users: '3 users',
    locations: '1 location',
    features: [
      'Unlimited PA queries',
      'Denial analysis + appeal letters',
      'Basic payer intelligence',
      'Email support',
    ],
    featured: false,
  },
  {
    key: 'growth' as TierKey,
    name: 'Growth',
    price: '$5,000',
    users: '10 users',
    locations: '3 locations',
    features: [
      'Everything in Starter',
      'AR acceleration workflows',
      'Advanced payer matching',
      'Monthly ROI report',
      'Priority support',
    ],
    featured: true,
  },
  {
    key: 'enterprise' as TierKey,
    name: 'Enterprise',
    price: '$10,000',
    users: 'Unlimited',
    locations: 'Unlimited',
    features: [
      'Everything in Growth',
      'Full NexusAuth S1–S11 stack',
      'Custom payer rule config',
      'Dedicated account manager',
      'SLA guarantee',
      'EHR integration support',
    ],
    featured: false,
  },
]

interface Props {
  token: string
  onDismiss: () => void
  hardLock?: boolean
}

export default function PaywallModal({ token, onDismiss, hardLock = false }: Props) {
  const [loading, setLoading] = useState<TierKey | null>(null)
  const [error, setError] = useState('')

  async function handleCheckout(tier: TierKey) {
    setLoading(tier)
    setError('')

    try {
      const res = await fetch('/api/stripe/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier }),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Checkout failed')

      window.location.href = data.url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setLoading(null)
    }
  }

  return (
    <div className="modal-overlay" style={{ alignItems: 'flex-start', overflowY: 'auto', paddingTop: 32, paddingBottom: 32 }}>
      <div style={{ width: '100%', maxWidth: 960 }}>
        {/* Founding member banner */}
        <div
          style={{
            background: 'rgba(246,173,60,0.08)',
            border: '1px solid rgba(246,173,60,0.25)',
            borderRadius: 10,
            padding: '12px 20px',
            textAlign: 'center',
            marginBottom: 24,
            color: 'var(--gold)',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          ★ First 5 customers — 40% off locked forever as a Founding Member
        </div>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 10 }}>
            Unlock Full Access
          </h2>
          <p style={{ color: 'var(--gray-light)', fontSize: 15 }}>
            Start your 14-day free trial. No credit card required to start.
          </p>
        </div>

        {/* Tier cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 20,
            marginBottom: 24,
          }}
        >
          {TIERS.map((tier) => (
            <div
              key={tier.key}
              className={`tier-card${tier.featured ? ' featured' : ''}`}
            >
              {tier.featured && (
                <div
                  style={{
                    position: 'absolute',
                    top: -12,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'var(--green)',
                    color: '#0A0F1A',
                    fontSize: 11,
                    fontWeight: 700,
                    padding: '4px 14px',
                    borderRadius: 20,
                    letterSpacing: '0.05em',
                  }}
                >
                  MOST POPULAR
                </div>
              )}

              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 13, color: 'var(--gray-light)', fontWeight: 600, marginBottom: 6 }}>
                  {tier.name}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span style={{ fontSize: 30, fontWeight: 800 }}>{tier.price}</span>
                  <span style={{ color: 'var(--gray)', fontSize: 13 }}>/mo</span>
                </div>
                <div style={{ color: 'var(--gray)', fontSize: 12, marginTop: 4 }}>
                  {tier.users} · {tier.locations}
                </div>
              </div>

              <ul style={{ listStyle: 'none', marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {tier.features.map((f) => (
                  <li key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 13, color: 'var(--gray-light)' }}>
                    <span style={{ color: 'var(--green)', flexShrink: 0, marginTop: 1 }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                className={tier.featured ? 'btn-primary' : 'btn-ghost'}
                disabled={loading !== null}
                onClick={() => handleCheckout(tier.key)}
                style={{ borderRadius: 8, padding: '11px 20px', fontSize: 13, width: '100%' }}
              >
                {loading === tier.key ? 'Redirecting...' : 'Start 14-Day Free Trial'}
              </button>
            </div>
          ))}
        </div>

        {error && (
          <p style={{ color: 'var(--red)', fontSize: 13, textAlign: 'center', marginBottom: 16 }}>
            {error}
          </p>
        )}

        {!hardLock && (
          <div style={{ textAlign: 'center' }}>
            <button
              onClick={onDismiss}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--gray)',
                fontSize: 13,
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Maybe later
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
