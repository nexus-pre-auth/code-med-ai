import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase-server'
import { generateEmbedding } from '@/lib/embeddings'

export async function POST(req: NextRequest) {
  const authHeader = req.headers.get('authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const token = authHeader.replace('Bearer ', '')
  const supabaseAdmin = createAdminClient()

  const {
    data: { user },
  } = await supabaseAdmin.auth.getUser(token)
  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: { id: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { id } = body
  if (!id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 })
  }

  // Fetch the entry
  const { data: entry, error: fetchError } = await supabaseAdmin
    .from('knowledge_base')
    .select('title, content')
    .eq('id', id)
    .single()

  if (fetchError || !entry) {
    return NextResponse.json({ error: 'Entry not found' }, { status: 404 })
  }

  // Generate embedding from title + content
  const inputText = `${entry.title}: ${entry.content}`
  const embedding = await generateEmbedding(inputText)

  // Store embedding
  const { error: updateError } = await supabaseAdmin
    .from('knowledge_base')
    .update({ embedding, updated_at: new Date().toISOString() })
    .eq('id', id)

  if (updateError) {
    console.error('Embedding update error:', updateError)
    return NextResponse.json({ error: 'Failed to store embedding' }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
