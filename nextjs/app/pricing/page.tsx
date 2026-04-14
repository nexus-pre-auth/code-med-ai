'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import type { TierKey } from '@/lib/stripe'

const TIERS = [
  {
    key: 'starter' as TierKey,
    name: 'Starter',
    price: 2500,
    displayPrice: '$2,500',
    users: '3 users',
    locations: '1 location',
    featured: false,
    features: [
      'Unlimited PA queries',
      'Denial analysis + appeal letter generation',
      'Basic payer intelligence',
      'Email support',
    ],
  },
  {
    key: 'growth' as TierKey,
    name: 'Growth',
    price: 5000,
    displayPrice: '$5,000',
    users: '10 users',
    locations: '3 locations',
    featured: true,
    features: [
      'Everything in Starter',
      'AR acceleration workflows',
      'Advanced payer matching',
      'Monthly ROI report',
      'Priority support',
    ],
  },
  {
    key: 'enterprise' as TierKey,
    name: 'Enterprise',
    price: 10000,
    displayPrice: '$10,000',
    users: 'Unlimited',
    locations: 'Unlimited',
    featured: false,
    features: [
      'Everything in Growth',
      'Full NexusAuth S1–S11 stack',
      'Custom payer rule config',
      'Dedicated account manager',
      'SLA guarantee',
      'EHR integration support',
    ],
  },
]

export default function PricingPage() {
  const [claimVolume, setClaimVolume] = useState(500)
  const [avgClaimValue, setAvgClaimValue] = useState(350)
  const [checkoutLoading, setCheckoutLoading] = useState<TierKey | null>(null)
  const [error, setError] = useState('')

  const recoverable = Math.round(claimVolume * avgClaimValue * 0.23 * 0.68 * 12)
  const atRisk = Math.round(claimVolume * avgClaimValue * 0.23 * 12)

  async function handleCheckout(tier: TierKey) {
    setCheckoutLoading(tier)
    setError('')
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()

    if (!session) {
      window.location.href = `/auth?next=/pricing`
      return
    }

    try {
      const res = await fetch('/api/stripe/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ tier }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Checkout failed')
      window.location.href = data.url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setCheckoutLoading(null)
    }
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Nav */}
      <header
        className="glass-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 40px',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <a
          href="/"
          style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontWeight: 700,
            fontSize: 18,
            color: 'var(--green)',
            letterSpacing: '0.1em',
            textDecoration: 'none',
          }}
        >
          CODEMED
        </a>
        <div style={{ display: 'flex', gap: 12 }}>
          <a
            href="/auth"
            className="btn-ghost"
            style={{ borderRadius: 8, padding: '8px 20px', fontSize: 13, textDecoration: 'none' }}
          >
            Sign In
          </a>
          <a
            href="/auth"
            className="btn-primary"
            style={{ borderRadius: 8, padding: '8px 20px', fontSize: 13, textDecoration: 'none' }}
          >
            Start Free Trial
          </a>
        </div>
      </header>

      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '60px 24px 80px' }}>

        {/* Hero */}
        <div style={{ textAlign: 'center', marginBottom: 52 }}>
          <h1
            style={{
              fontSize: 'clamp(32px, 5vw, 52px)',
              fontWeight: 900,
              lineHeight: 1.15,
              marginBottom: 18,
            }}
          >
            AI Revenue Cycle Intelligence
            <br />
            <span style={{ color: 'var(--green)' }}>for Healthcare</span>
          </h1>
          <p
            style={{
              color: 'var(--gray-light)',
              fontSize: 17,
              lineHeight: 1.6,
              maxWidth: 560,
              margin: '0 auto 28px',
            }}
          >
            Prior auth automation, denial management, and AR acceleration — so your billing team stops chasing and starts closing.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a
              href="/auth"
              className="btn-primary"
              style={{ borderRadius: 10, padding: '13px 28px', fontSize: 15, textDecoration: 'none' }}
            >
              Start Free 14-Day Trial
            </a>
            <a
              href="#pricing"
              className="btn-ghost"
              style={{ borderRadius: 10, padding: '13px 28px', fontSize: 15, textDecoration: 'none' }}
            >
              See Pricing
            </a>
          </div>
        </div>

        {/* Stats */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 16,
            marginBottom: 64,
          }}
        >
          {[
            { value: '94%', label: 'PA Approval Rate', sub: 'vs 71% industry avg' },
            { value: '6.2h', label: 'PA Turnaround', sub: 'vs 4.8 day industry avg' },
            { value: '$206K', label: 'Monthly Protected', sub: 'per avg practice' },
            { value: 'HIPAA', label: 'Compliant', sub: 'SOC 2 in progress' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="card"
              style={{ padding: '20px 24px', textAlign: 'center' }}
            >
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 900,
                  color: 'var(--green)',
                  fontFamily: 'IBM Plex Mono, monospace',
                  marginBottom: 4,
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 3 }}>{stat.label}</div>
              <div style={{ fontSize: 11, color: 'var(--gray)' }}>{stat.sub}</div>
            </div>
          ))}
        </div>

        {/* Founding member banner */}
        <div
          style={{
            background: 'rgba(246,173,60,0.07)',
            border: '1px solid rgba(246,173,60,0.22)',
            borderRadius: 12,
            padding: '16px 24px',
            textAlign: 'center',
            marginBottom: 36,
          }}
        >
          <span style={{ color: 'var(--gold)', fontWeight: 700, fontSize: 14 }}>
            ★ Founding Member Offer
          </span>
          <span style={{ color: 'var(--gray-light)', fontSize: 13, marginLeft: 10 }}>
            First 5 customers get 40% off locked forever. No code needed — applied automatically.
          </span>
        </div>

        {/* Pricing cards */}
        <div
          id="pricing"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 24,
            marginBottom: 72,
          }}
        >
          {TIERS.map((tier) => (
            <div
              key={tier.key}
              className={`tier-card card-accent${tier.featured ? ' featured' : ''}`}
              style={{ padding: 32, position: 'relative' }}
            >
              {tier.featured && (
                <div
                  style={{
                    position: 'absolute',
                    top: -13,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'var(--green)',
                    color: '#0A0F1A',
                    fontSize: 10,
                    fontWeight: 800,
                    padding: '4px 14px',
                    borderRadius: 20,
                    letterSpacing: '0.06em',
                    whiteSpace: 'nowrap',
                  }}
                >
                  MOST POPULAR
                </div>
              )}

              <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 13, color: 'var(--gray-light)', fontWeight: 600, marginBottom: 8 }}>
                  {tier.name}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 5, marginBottom: 4 }}>
                  <span style={{ fontSize: 34, fontWeight: 900 }}>{tier.displayPrice}</span>
                  <span style={{ color: 'var(--gray)', fontSize: 13 }}>/month</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--gray)' }}>
                  {tier.users} · {tier.locations}
                </div>
              </div>

              <ul
                style={{
                  listStyle: 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  marginBottom: 28,
                  flex: 1,
                }}
              >
                {tier.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 8,
                      fontSize: 13,
                      color: 'var(--gray-light)',
                      lineHeight: 1.45,
                    }}
                  >
                    <span style={{ color: 'var(--green)', flexShrink: 0, fontWeight: 700, marginTop: 1 }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              {error && checkoutLoading === tier.key && (
                <p style={{ color: 'var(--red)', fontSize: 12, marginBottom: 10 }}>{error}</p>
              )}

              <button
                onClick={() => handleCheckout(tier.key)}
                disabled={checkoutLoading !== null}
                className={tier.featured ? 'btn-primary' : 'btn-ghost'}
                style={{ borderRadius: 10, padding: '12px 20px', fontSize: 13, width: '100%' }}
              >
                {checkoutLoading === tier.key ? 'Redirecting...' : 'Start 14-Day Free Trial'}
              </button>
            </div>
          ))}
        </div>

        {/* ROI Calculator */}
        <div
          className="card card-accent"
          style={{ padding: '40px 40px', maxWidth: 680, margin: '0 auto', textAlign: 'center' }}
        >
          <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Revenue Impact Calculator</h2>
          <p style={{ color: 'var(--gray-light)', fontSize: 13, marginBottom: 32 }}>
            See how much revenue you&apos;re leaving on the table each year.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 32 }}>
            <div style={{ textAlign: 'left' }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 8, fontWeight: 500 }}>
                Monthly Claim Volume
              </label>
              <input
                type="number"
                className="input-dark"
                value={claimVolume}
                min={1}
                onChange={(e) => setClaimVolume(Math.max(1, Number(e.target.value)))}
              />
            </div>
            <div style={{ textAlign: 'left' }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 8, fontWeight: 500 }}>
                Average Claim Value ($)
              </label>
              <input
                type="number"
                className="input-dark"
                value={avgClaimValue}
                min={1}
                onChange={(e) => setAvgClaimValue(Math.max(1, Number(e.target.value)))}
              />
            </div>
          </div>

          <div
            style={{
              background: 'var(--surface)',
              borderRadius: 12,
              padding: '24px 28px',
              border: '1px solid var(--border)',
              marginBottom: 24,
            }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--gray)', marginBottom: 4 }}>Annual Revenue at Risk</div>
                <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--red)', fontFamily: 'IBM Plex Mono' }}>
                  ${atRisk.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--gray)', marginBottom: 4 }}>Projected CodeMed Recovery</div>
                <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--green)', fontFamily: 'IBM Plex Mono' }}>
                  ${recoverable.toLocaleString()}
                </div>
              </div>
            </div>
            <p style={{ fontSize: 13, color: 'var(--gray-light)', lineHeight: 1.5 }}>
              Based on your numbers, you&apos;re likely leaving{' '}
              <strong style={{ color: 'var(--white)' }}>${recoverable.toLocaleString()}</strong> on the table annually.
              CodeMed AI recovers this through prior auth automation, denial appeals, and AR acceleration.
            </p>
          </div>

          <a
            href="/auth"
            className="btn-primary"
            style={{ borderRadius: 10, padding: '13px 28px', fontSize: 14, textDecoration: 'none', display: 'inline-block' }}
          >
            Start Free 14-Day Trial
          </a>
          <p style={{ fontSize: 11, color: 'var(--gray)', marginTop: 10 }}>
            No credit card required · Cancel anytime
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border)',
          padding: '24px 40px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div
          style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontWeight: 700,
            fontSize: 14,
            color: 'var(--green)',
            letterSpacing: '0.08em',
          }}
        >
          CODEMED
        </div>
        <div style={{ fontSize: 12, color: 'var(--gray)' }}>
          © {new Date().getFullYear()} CodeMed Group · codemedgroup.com · HIPAA Aware
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <a href="/auth" style={{ fontSize: 12, color: 'var(--gray)', textDecoration: 'none' }}>Sign In</a>
          <a href="/pricing" style={{ fontSize: 12, color: 'var(--gray)', textDecoration: 'none' }}>Pricing</a>
        </div>
      </footer>
    </div>
  )
}
