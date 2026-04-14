import { NextRequest, NextResponse } from 'next/server'
import Anthropic from '@anthropic-ai/sdk'
import { createAdminClient } from '@/lib/supabase-server'
import { generateSessionSummary } from '@/lib/memory'
import type { Message } from '@/lib/supabase'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! })

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

  let body: { sessionId: string; messages: Message[] }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { sessionId, messages } = body
  if (!sessionId || !messages?.length) {
    return NextResponse.json({ ok: true, summary: '' })
  }

  const summary = await generateSessionSummary(anthropic, messages)

  if (summary) {
    await supabaseAdmin
      .from('chat_sessions')
      .update({ summary, updated_at: new Date().toISOString() })
      .eq('id', sessionId)
      .eq('user_id', user.id)
  }

  return NextResponse.json({ ok: true, summary })
}
