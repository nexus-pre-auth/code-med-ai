'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import type { Subscription, Message } from '@/lib/supabase'
import { isSubscriptionActive } from '@/lib/supabase'
import { CHIP_FOLLOW_UPS, type TopicKey } from '@/lib/prompts'
import SubscriptionBadge from './SubscriptionBadge'
import LeadGate from './LeadGate'
import ChipRow from './ChipRow'
import TypingIndicator from './TypingIndicator'
import PaywallModal from './PaywallModal'
import CTACard from './CTACard'
import PDFExportButton from './PDFExportButton'

interface Lead {
  id: string
  name: string
  org: string
  role: string
}

interface Props {
  userEmail: string
  initialSubscription: Subscription | null
}

function generateSessionId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.07);padding:2px 5px;border-radius:4px;font-family:IBM Plex Mono,monospace;font-size:0.9em">$1</code>')
    .replace(/\n\n/g, '</p><p style="margin-top:10px">')
    .replace(/\n/g, '<br/>')
}

export default function ChatShell({ userEmail, initialSubscription }: Props) {
  const router = useRouter()
  const supabase = createClient()

  const [token, setToken] = useState<string | null>(null)
  const [lead, setLead] = useState<Lead | null>(null)
  const [showLeadGate, setShowLeadGate] = useState(false)
  const [subscription, setSubscription] = useState<Subscription | null>(initialSubscription)

  const [sessionId] = useState(generateSessionId)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedTopic, setSelectedTopic] = useState<TopicKey | null>(null)
  const [topicContext, setTopicContext] = useState<{ key: TopicKey; label: string } | null>(null)

  const [showPaywall, setShowPaywall] = useState(false)
  const [paywallDismissed, setPaywallDismissed] = useState(false)
  const [showCTA, setShowCTA] = useState(false)
  const [ctaShown, setCtaShown] = useState(false)

  const [trialExpired, setTrialExpired] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const userMessageCount = messages.filter((m) => m.role === 'user').length

  // Get session token
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.push('/auth'); return }
      setToken(session.access_token)
    })
  }, [])

  // Check for trial expired hard lock
  useEffect(() => {
    if (subscription?.status === 'trialing' && subscription.trial_end) {
      const expired = new Date(subscription.trial_end) <= new Date()
      setTrialExpired(expired)
      if (expired) setShowPaywall(true)
    }
  }, [subscription])

  // Fetch lead record
  useEffect(() => {
    if (!token) return
    fetch('/api/leads', { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then(({ lead: l }) => {
        if (l) {
          setLead(l)
        } else {
          setShowLeadGate(true)
        }
      })
  }, [token])

  // Welcome message after lead loaded
  useEffect(() => {
    if (!lead || messages.length > 0) return
    const firstName = lead.name.split(' ')[0]
    const welcome: Message = {
      role: 'assistant',
      content: `Welcome back, **${firstName}**. I'm CodeMed AI — your senior RCM consultant for **${lead.org}**.\n\nI can help with prior authorization, denial management, AR acceleration, payer intelligence, and coding accuracy. What's your biggest revenue cycle challenge right now?`,
      timestamp: new Date().toISOString(),
    }
    setMessages([welcome])
  }, [lead])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Save summary on unload
  useEffect(() => {
    const handleUnload = () => {
      if (!token || messages.length < 2) return
      const body = JSON.stringify({ sessionId, messages })
      navigator.sendBeacon('/api/sessions/summary', body)
    }
    window.addEventListener('beforeunload', handleUnload)
    return () => window.removeEventListener('beforeunload', handleUnload)
  }, [token, sessionId, messages])

  const sendMessage = useCallback(
    async (content: string, overrideContext?: { key: TopicKey; label: string } | null) => {
      if (!token || !content.trim() || loading) return

      const ctx = overrideContext !== undefined ? overrideContext : topicContext
      const userMsg: Message = { role: 'user', content: content.trim(), timestamp: new Date().toISOString() }
      const newMessages = [...messages, userMsg]
      setMessages(newMessages)
      setInput('')
      setLoading(true)

      // Resize textarea
      if (textareaRef.current) {
        textareaRef.current.style.height = '42px'
      }

      const nextUserCount = newMessages.filter((m) => m.role === 'user').length

      // Paywall gate: message 4+ requires subscription
      if (nextUserCount > 3 && !isSubscriptionActive(subscription) && !paywallDismissed) {
        setLoading(false)
        setShowPaywall(true)
        return
      }

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            messages: newMessages,
            sessionId,
            context: ctx,
            messageCount: nextUserCount,
          }),
        })

        if (res.status === 402) {
          setShowPaywall(true)
          setLoading(false)
          return
        }

        const data: { text: string; isAppealLetter: boolean } = await res.json()

        const assistantMsg: Message = {
          role: 'assistant',
          content: data.text,
          timestamp: new Date().toISOString(),
          isAppealLetter: data.isAppealLetter,
        }

        const finalMessages = [...newMessages, assistantMsg]
        setMessages(finalMessages)

        // Show CTA once after 4th exchange
        if (nextUserCount >= 4 && !ctaShown) {
          setShowCTA(true)
          setCtaShown(true)
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'I encountered an error. Please try again.', timestamp: new Date().toISOString() },
        ])
      } finally {
        setLoading(false)
      }
    },
    [token, messages, loading, topicContext, subscription, paywallDismissed, sessionId, ctaShown]
  )

  function handleChipSelect(key: TopicKey, label: string) {
    setSelectedTopic(key)
    const ctx = { key, label }
    setTopicContext(ctx)

    // Add user chip-click as message
    const userMsg: Message = { role: 'user', content: label, timestamp: new Date().toISOString() }
    const followUp: Message = {
      role: 'assistant',
      content: CHIP_FOLLOW_UPS[key],
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg, followUp])
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    // Auto-grow
    e.target.style.height = '42px'
    e.target.style.height = Math.min(e.target.scrollHeight, 110) + 'px'
  }

  async function handleSignOut() {
    await supabase.auth.signOut()
    router.push('/auth')
  }

  async function handleManageBilling() {
    if (!token) return
    const res = await fetch('/api/stripe/portal', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    const { url } = await res.json()
    if (url) window.location.href = url
  }

  const showChips = messages.length <= 1 && !selectedTopic

  return (
    <>
      {/* Lead Gate */}
      {showLeadGate && token && (
        <LeadGate
          token={token}
          onComplete={(id, name) => {
            setLead({ id, name, org: '', role: '' })
            setShowLeadGate(false)
          }}
        />
      )}

      {/* Paywall Modal */}
      {showPaywall && token && (
        <PaywallModal
          token={token}
          hardLock={trialExpired}
          onDismiss={() => {
            if (!trialExpired) {
              setShowPaywall(false)
              setPaywallDismissed(true)
            }
          }}
        />
      )}

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          maxWidth: 800,
          margin: '0 auto',
        }}
      >
        {/* Header */}
        <header
          className="glass-header"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 20px',
            flexShrink: 0,
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span
              style={{
                fontFamily: 'IBM Plex Mono, monospace',
                fontWeight: 700,
                fontSize: 16,
                color: 'var(--green)',
                letterSpacing: '0.08em',
              }}
            >
              CODEMED
            </span>
            {/* Live AI pill */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 10px',
                background: 'rgba(0,212,160,0.08)',
                border: '1px solid var(--green-border)',
                borderRadius: 20,
                fontSize: 11,
                color: 'var(--green)',
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: 'var(--green)',
                  display: 'inline-block',
                  animation: 'typingBounce 2s ease-in-out infinite',
                }}
              />
              AI Live
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: 'var(--gray)' }}>{userEmail}</span>
            <SubscriptionBadge subscription={subscription} />
            {subscription && (
              <button
                onClick={handleManageBilling}
                className="btn-ghost"
                style={{ borderRadius: 6, padding: '5px 12px', fontSize: 11 }}
              >
                Billing
              </button>
            )}
            <a
              href="/documents"
              className="btn-ghost"
              style={{ borderRadius: 6, padding: '5px 12px', fontSize: 11, textDecoration: 'none' }}
            >
              Docs
            </a>
            <button
              onClick={handleSignOut}
              className="btn-ghost"
              style={{ borderRadius: 6, padding: '5px 12px', fontSize: 11 }}
            >
              Sign Out
            </button>
          </div>
        </header>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className="fade-in"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                gap: 8,
              }}
            >
              {msg.role === 'assistant' ? (
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  {/* Avatar */}
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
                  <div>
                    <div
                      className="bubble-bot"
                      dangerouslySetInnerHTML={{
                        __html: `<p>${renderMarkdown(msg.content)}</p>`,
                      }}
                    />
                    {msg.isAppealLetter && token && (
                      <div style={{ marginTop: 10 }}>
                        <PDFExportButton
                          content={msg.content}
                          title="Appeal Letter"
                          token={token}
                          sessionId={sessionId}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="bubble-user">{msg.content}</div>
              )}
            </div>
          ))}

          {/* Chip row after welcome */}
          {showChips && (
            <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
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
                <div style={{ paddingTop: 4 }}>
                  <ChipRow
                    onSelect={handleChipSelect}
                    disabled={loading}
                    selected={selectedTopic}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Typing indicator */}
          {loading && <TypingIndicator />}

          {/* CTA Card */}
          {showCTA && !isSubscriptionActive(subscription) && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', paddingLeft: 38 }}>
              <CTACard calendlyUrl={process.env.NEXT_PUBLIC_CALENDLY_URL} />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div
          style={{
            padding: '12px 20px 16px',
            borderTop: '1px solid var(--border)',
            background: 'rgba(10,15,26,0.9)',
            backdropFilter: 'blur(12px)',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              display: 'flex',
              gap: 10,
              alignItems: 'flex-end',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 12,
              padding: '8px 12px',
              transition: 'border-color 0.15s',
            }}
            onFocus={() => {}}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder={selectedTopic ? 'Ask a follow-up question...' : 'Ask anything about prior auth, denials, AR...'}
              disabled={loading || !token || showLeadGate}
              rows={1}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--white)',
                fontSize: 14,
                fontFamily: 'Inter, sans-serif',
                resize: 'none',
                minHeight: 42,
                maxHeight: 110,
                lineHeight: 1.5,
                padding: '6px 0',
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading || !token}
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background:
                  input.trim() && !loading
                    ? 'linear-gradient(135deg, #00D4A0, #00B386)'
                    : 'rgba(255,255,255,0.06)',
                border: 'none',
                color: input.trim() && !loading ? '#0A0F1A' : 'var(--gray)',
                cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                transition: 'all 0.15s',
                fontSize: 16,
              }}
            >
              ↑
            </button>
          </div>

          {/* PHI disclaimer */}
          <p
            style={{
              fontSize: 11,
              color: 'var(--gray)',
              textAlign: 'center',
              marginTop: 8,
              lineHeight: 1.4,
            }}
          >
            Conversations are saved to improve your experience. Do not enter patient names or member IDs.
          </p>
        </div>
      </div>
    </>
  )
}
