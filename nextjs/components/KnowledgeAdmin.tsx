'use client'

import { useState, useEffect, useCallback } from 'react'

const CATEGORIES = [
  'Payer Policies',
  'Denial Codes',
  'NexusAuth Modules',
  'Clinical Criteria',
  'LCD/NCD Policies',
  'Appeal Templates',
  'ElderlyAI',
  'Custom',
]

interface KnowledgeEntry {
  id: string
  category: string
  title: string
  content: string
  tags: string[]
  source: string
  active: boolean
  created_at: string
  updated_at: string
}

interface Props {
  token: string
}

type Tab = 'library' | 'add' | 'upload' | 'preview'

export default function KnowledgeAdmin({ token }: Props) {
  const [tab, setTab] = useState<Tab>('library')
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Add form state
  const [addForm, setAddForm] = useState({
    category: '',
    title: '',
    content: '',
    tags: '',
    source: 'Manual',
  })
  const [addLoading, setAddLoading] = useState(false)

  // Edit state
  const [editId, setEditId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<KnowledgeEntry>>({})

  // Upload state
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (categoryFilter !== 'all') params.set('category', categoryFilter)
    if (search) params.set('search', search)

    const res = await fetch(`/api/knowledge?${params}`, {
      headers: authHeaders,
    })
    const data = await res.json()
    setEntries(data.entries || [])
    setLoading(false)
  }, [categoryFilter, search, token])

  useEffect(() => {
    if (tab === 'library') fetchEntries()
  }, [tab, fetchEntries])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setAddLoading(true)
    setError('')
    setSuccess('')

    try {
      // Create entry
      const res = await fetch('/api/knowledge', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          category: addForm.category,
          title: addForm.title,
          content: addForm.content,
          tags: addForm.tags.split(',').map((t) => t.trim()).filter(Boolean),
          source: addForm.source,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error)

      // Generate embedding
      await fetch('/api/knowledge/embed', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ id: data.id }),
      })

      setSuccess(`"${addForm.title}" added and embedded successfully.`)
      setAddForm({ category: '', title: '', content: '', tags: '', source: 'Manual' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add entry')
    } finally {
      setAddLoading(false)
    }
  }

  async function handleToggleActive(entry: KnowledgeEntry) {
    await fetch('/api/knowledge', {
      method: 'PATCH',
      headers: authHeaders,
      body: JSON.stringify({ id: entry.id, active: !entry.active }),
    })
    fetchEntries()
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this knowledge entry? This cannot be undone.')) return
    await fetch(`/api/knowledge?id=${id}`, { method: 'DELETE', headers: authHeaders })
    fetchEntries()
  }

  async function handleEdit(entry: KnowledgeEntry) {
    if (editId === entry.id) {
      // Save
      await fetch('/api/knowledge', {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ id: entry.id, ...editForm }),
      })
      // Re-embed
      await fetch('/api/knowledge/embed', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ id: entry.id }),
      })
      setEditId(null)
      setEditForm({})
      fetchEntries()
    } else {
      setEditId(entry.id)
      setEditForm({ title: entry.title, content: entry.content, category: entry.category })
    }
  }

  async function handleFileUpload(files: FileList) {
    if (!files.length) return
    setUploadLoading(true)
    setUploadProgress('')

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      setUploadProgress(`Processing ${i + 1}/${files.length}: ${file.name}...`)

      const text = await file.text()

      // Chunk by 1000 chars
      const chunkSize = 1000
      const chunks: string[] = []
      for (let j = 0; j < text.length; j += chunkSize) {
        chunks.push(text.slice(j, j + chunkSize))
      }

      for (let k = 0; k < chunks.length; k++) {
        const res = await fetch('/api/knowledge', {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify({
            category: 'Custom',
            title: `${file.name} — Part ${k + 1}`,
            content: chunks[k],
            tags: [file.name],
            source: file.name,
          }),
        })
        const data = await res.json()
        if (data.id) {
          await fetch('/api/knowledge/embed', {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({ id: data.id }),
          })
        }
      }
    }

    setUploadProgress(`Upload complete — ${files.length} file(s) processed.`)
    setUploadLoading(false)
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>Knowledge Base Admin</h1>
        <p style={{ color: 'var(--gray-light)', fontSize: 13 }}>
          Manage the knowledge that CodeMed AI uses to answer questions.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 4 }}>
        {(['library', 'add', 'upload', 'preview'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 18px',
              borderRadius: '8px 8px 0 0',
              border: 'none',
              background: tab === t ? 'var(--card)' : 'transparent',
              color: tab === t ? 'var(--white)' : 'var(--gray)',
              fontSize: 13,
              fontWeight: tab === t ? 600 : 400,
              cursor: 'pointer',
              borderBottom: tab === t ? '2px solid var(--green)' : '2px solid transparent',
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Library Tab */}
      {tab === 'library' && (
        <div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
            <input
              className="input-dark"
              placeholder="Search titles..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchEntries()}
              style={{ maxWidth: 280 }}
            />
            <select
              className="input-dark"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              style={{ maxWidth: 200, cursor: 'pointer' }}
            >
              <option value="all">All Categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <button className="btn-ghost" onClick={fetchEntries} style={{ borderRadius: 8, padding: '10px 16px', fontSize: 13 }}>
              Search
            </button>
          </div>

          {loading ? (
            <div style={{ color: 'var(--gray)', fontSize: 13, padding: 20 }}>Loading...</div>
          ) : entries.length === 0 ? (
            <div style={{ color: 'var(--gray)', fontSize: 13, padding: 20 }}>No entries found.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {entries.map((entry) => (
                <div key={entry.id} className="card" style={{ padding: '16px 20px' }}>
                  {editId === entry.id ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      <input
                        className="input-dark"
                        value={editForm.title || ''}
                        onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                        placeholder="Title"
                      />
                      <textarea
                        className="input-dark"
                        value={editForm.content || ''}
                        onChange={(e) => setEditForm((f) => ({ ...f, content: e.target.value }))}
                        rows={4}
                        style={{ resize: 'vertical' }}
                        placeholder="Content"
                      />
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn-primary" onClick={() => handleEdit(entry)} style={{ borderRadius: 8, padding: '8px 16px', fontSize: 12 }}>Save</button>
                        <button className="btn-ghost" onClick={() => { setEditId(null); setEditForm({}) }} style={{ borderRadius: 8, padding: '8px 16px', fontSize: 12 }}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <span style={{ fontSize: 10, color: 'var(--green)', background: 'var(--green-glow)', padding: '2px 8px', borderRadius: 20, fontFamily: 'IBM Plex Mono' }}>
                            {entry.category}
                          </span>
                          {!entry.active && (
                            <span style={{ fontSize: 10, color: 'var(--gray)', background: 'rgba(107,130,153,0.1)', padding: '2px 8px', borderRadius: 20 }}>
                              PAUSED
                            </span>
                          )}
                        </div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{entry.title}</div>
                        <div style={{ fontSize: 12, color: 'var(--gray-light)', lineHeight: 1.5 }}>
                          {entry.content.slice(0, 120)}{entry.content.length > 120 ? '...' : ''}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                        <button className="btn-ghost" onClick={() => handleEdit(entry)} style={{ borderRadius: 6, padding: '6px 12px', fontSize: 11 }}>Edit</button>
                        <button className="btn-ghost" onClick={() => handleToggleActive(entry)} style={{ borderRadius: 6, padding: '6px 12px', fontSize: 11 }}>
                          {entry.active ? 'Pause' : 'Resume'}
                        </button>
                        <button onClick={() => handleDelete(entry.id)} style={{ background: 'rgba(252,90,90,0.08)', border: '1px solid rgba(252,90,90,0.2)', color: 'var(--red)', borderRadius: 6, padding: '6px 12px', fontSize: 11, cursor: 'pointer' }}>
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Tab */}
      {tab === 'add' && (
        <div className="card" style={{ padding: 28, maxWidth: 680 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>Add Knowledge Entry</h2>
          {error && <p style={{ color: 'var(--red)', fontSize: 13, marginBottom: 16 }}>{error}</p>}
          {success && <p style={{ color: 'var(--green)', fontSize: 13, marginBottom: 16 }}>{success}</p>}

          <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6 }}>Category</label>
              <select className="input-dark" value={addForm.category} onChange={(e) => setAddForm((f) => ({ ...f, category: e.target.value }))} required style={{ cursor: 'pointer' }}>
                <option value="">Select category...</option>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6 }}>Title</label>
              <input className="input-dark" value={addForm.title} onChange={(e) => setAddForm((f) => ({ ...f, title: e.target.value }))} placeholder="e.g., Aetna Prior Auth 2026" required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6 }}>Content</label>
              <textarea className="input-dark" value={addForm.content} onChange={(e) => setAddForm((f) => ({ ...f, content: e.target.value }))} rows={6} style={{ resize: 'vertical' }} placeholder="Knowledge content..." required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6 }}>Tags (comma-separated)</label>
              <input className="input-dark" value={addForm.tags} onChange={(e) => setAddForm((f) => ({ ...f, tags: e.target.value }))} placeholder="prior-auth, aetna, cardiology" />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--gray-light)', marginBottom: 6 }}>Source</label>
              <input className="input-dark" value={addForm.source} onChange={(e) => setAddForm((f) => ({ ...f, source: e.target.value }))} placeholder="Manual" />
            </div>
            <button type="submit" className="btn-primary" disabled={addLoading} style={{ borderRadius: 8, padding: '12px 24px', fontSize: 13 }}>
              {addLoading ? 'Saving & Embedding...' : 'Save Entry'}
            </button>
          </form>
        </div>
      )}

      {/* Upload Tab */}
      {tab === 'upload' && (
        <div className="card" style={{ padding: 32, maxWidth: 560, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>📄</div>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Upload Documents</h2>
          <p style={{ color: 'var(--gray-light)', fontSize: 13, marginBottom: 24, lineHeight: 1.5 }}>
            Upload PDF, DOC, or TXT files. Each file is chunked, embedded, and added as knowledge entries automatically.
          </p>
          <input
            type="file"
            accept=".txt,.pdf,.doc,.docx"
            multiple
            disabled={uploadLoading}
            onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
            style={{ display: 'none' }}
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            style={{
              display: 'inline-block',
              background: 'linear-gradient(135deg, var(--green), var(--green2))',
              color: '#0A0F1A',
              fontWeight: 700,
              borderRadius: 8,
              padding: '11px 24px',
              cursor: uploadLoading ? 'not-allowed' : 'pointer',
              fontSize: 13,
              opacity: uploadLoading ? 0.5 : 1,
            }}
          >
            {uploadLoading ? 'Processing...' : 'Choose Files'}
          </label>
          {uploadProgress && (
            <p style={{ color: 'var(--green)', fontSize: 13, marginTop: 16 }}>{uploadProgress}</p>
          )}
        </div>
      )}

      {/* Preview Tab */}
      {tab === 'preview' && (
        <PreviewTab token={token} />
      )}
    </div>
  )
}

function PreviewTab({ token }: { token: string }) {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetch('/api/knowledge?category=all', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => { setEntries(d.entries || []); setLoading(false) })
  }, [token])

  const grouped = entries.reduce<Record<string, KnowledgeEntry[]>>((acc, e) => {
    if (!e.active) return acc
    if (!acc[e.category]) acc[e.category] = []
    acc[e.category].push(e)
    return acc
  }, {})

  const promptText = Object.entries(grouped)
    .map(([cat, items]) =>
      `## ${cat}\n${items.map((i) => `### ${i.title}\n${i.content}`).join('\n\n')}`
    )
    .join('\n\n')

  function copyToClipboard() {
    navigator.clipboard.writeText(promptText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Live Prompt Preview</h2>
        <button className="btn-ghost" onClick={copyToClipboard} style={{ borderRadius: 8, padding: '8px 16px', fontSize: 12 }}>
          {copied ? 'Copied!' : 'Copy to Clipboard'}
        </button>
      </div>
      {loading ? (
        <div style={{ color: 'var(--gray)', fontSize: 13 }}>Loading...</div>
      ) : (
        <pre
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: 20,
            fontSize: 12,
            lineHeight: 1.6,
            color: 'var(--gray-light)',
            overflowX: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {promptText || 'No active entries.'}
        </pre>
      )}
    </div>
  )
}
