import { redirect } from 'next/navigation'
import { createServerClient, createAdminClient } from '@/lib/supabase-server'
import DocumentCard from '@/components/DocumentCard'
import type { Document } from '@/lib/supabase'

export const metadata = { title: 'Documents — CodeMed' }

export default async function DocumentsPage() {
  const supabase = createServerClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) redirect('/auth')

  const supabaseAdmin = createAdminClient()
  const { data: documents } = await supabaseAdmin
    .from('documents')
    .select('*')
    .eq('user_id', session.user.id)
    .order('created_at', { ascending: false })

  const docs = (documents ?? []) as Document[]

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header
        className="glass-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 28px',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <a
          href="/chat"
          style={{
            fontFamily: 'IBM Plex Mono, monospace',
            fontWeight: 700,
            fontSize: 16,
            color: 'var(--green)',
            letterSpacing: '0.08em',
            textDecoration: 'none',
          }}
        >
          CODEMED
        </a>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <a
            href="/chat"
            className="btn-ghost"
            style={{
              borderRadius: 8,
              padding: '7px 16px',
              fontSize: 13,
              textDecoration: 'none',
            }}
          >
            ← Back to Chat
          </a>
        </div>
      </header>

      <div style={{ maxWidth: 800, margin: '0 auto', padding: '36px 24px' }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 6 }}>Saved Documents</h1>
          <p style={{ color: 'var(--gray-light)', fontSize: 13 }}>
            Appeal letters and PA packages generated in your sessions.
          </p>
        </div>

        {docs.length === 0 ? (
          <div
            className="card"
            style={{
              padding: '48px 32px',
              textAlign: 'center',
              color: 'var(--gray)',
            }}
          >
            <div style={{ fontSize: 40, marginBottom: 16 }}>📄</div>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8, color: 'var(--gray-light)' }}>
              No documents yet
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.6, maxWidth: 320, margin: '0 auto' }}>
              Generate an appeal letter in the chat to save it here. CodeMed AI detects appeal letters automatically and offers a PDF export.
            </p>
            <a
              href="/chat"
              className="btn-primary"
              style={{
                display: 'inline-block',
                borderRadius: 8,
                padding: '11px 24px',
                fontSize: 13,
                textDecoration: 'none',
                marginTop: 20,
              }}
            >
              Go to Chat
            </a>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {docs.map((doc) => (
              <DocumentCard key={doc.id} document={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
