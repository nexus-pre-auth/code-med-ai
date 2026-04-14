'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

type Mode = 'signin' | 'signup'

export default function AuthForm() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const supabase = createClient()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    if (mode === 'signup') {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/chat` },
      })

      if (error) {
        setError(error.message)
      } else {
        setSuccess('Check your email for a confirmation link to activate your account.')
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password })

      if (error) {
        setError(error.message)
      } else {
        router.push('/chat')
        router.refresh()
      }
    }

    setLoading(false)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div className="card card-accent" style={{ width: '100%', maxWidth: 440, padding: 40 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              fontSize: 24,
              fontWeight: 900,
              color: 'var(--green)',
              letterSpacing: '0.1em',
              fontFamily: 'IBM Plex Mono, monospace',
            }}
          >
            CODEMED
          </div>
          <div style={{ color: 'var(--gray)', fontSize: 12, marginTop: 4, letterSpacing: '0.04em' }}>
            AI REVENUE CYCLE INTELLIGENCE
          </div>
        </div>

        {/* Mode toggle */}
        <div
          style={{
            display: 'flex',
            background: 'var(--surface)',
            borderRadius: 10,
            padding: 4,
            marginBottom: 28,
            border: '1px solid var(--border)',
          }}
        >
          {(['signin', 'signup'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(''); setSuccess('') }}
              style={{
                flex: 1,
                padding: '8px 16px',
                borderRadius: 7,
                border: 'none',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
                background: mode === m ? 'var(--card)' : 'transparent',
                color: mode === m ? 'var(--white)' : 'var(--gray)',
                borderColor: mode === m ? 'var(--border)' : 'transparent',
              }}
            >
              {m === 'signin' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6, fontWeight: 500 }}>
              Email
            </label>
            <input
              className="input-dark"
              type="email"
              placeholder="you@yourpractice.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6, fontWeight: 500 }}>
              Password
            </label>
            <input
              className="input-dark"
              type="password"
              placeholder={mode === 'signup' ? 'Min 8 characters' : '••••••••'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={mode === 'signup' ? 8 : 1}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            />
          </div>

          {error && (
            <p style={{ color: 'var(--red)', fontSize: 13, padding: '10px 14px', background: 'rgba(252,90,90,0.08)', borderRadius: 8, border: '1px solid rgba(252,90,90,0.2)' }}>
              {error}
            </p>
          )}

          {success && (
            <p style={{ color: 'var(--green)', fontSize: 13, padding: '10px 14px', background: 'rgba(0,212,160,0.08)', borderRadius: 8, border: '1px solid var(--green-border)' }}>
              {success}
            </p>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ borderRadius: 8, padding: '13px 24px', fontSize: 14, marginTop: 4 }}
          >
            {loading
              ? 'Please wait...'
              : mode === 'signup'
              ? 'Create Account'
              : 'Sign In'}
          </button>
        </form>

        {/* Stats row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 8,
            marginTop: 28,
            paddingTop: 24,
            borderTop: '1px solid var(--border)',
          }}
        >
          {[
            { value: '94%', label: 'Approval Rate' },
            { value: '6.2h', label: 'PA Turnaround' },
            { value: '$206K', label: 'Monthly Protected' },
            { value: 'HIPAA', label: 'Compliant' },
          ].map((stat) => (
            <div key={stat.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--green)', fontFamily: 'IBM Plex Mono, monospace' }}>
                {stat.value}
              </div>
              <div style={{ fontSize: 10, color: 'var(--gray)', marginTop: 2, lineHeight: 1.3 }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
