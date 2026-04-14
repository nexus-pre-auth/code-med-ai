import { NextRequest, NextResponse } from 'next/server'
import Anthropic from '@anthropic-ai/sdk'
import { createAdminClient } from '@/lib/supabase-server'
import { buildSystemPrompt } from '@/lib/prompts'
import { searchKnowledge } from '@/lib/embeddings'
import { getRecentSessionSummary } from '@/lib/memory'
import { isSubscriptionActive } from '@/lib/supabase'
import type { Message } from '@/lib/supabase'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! })

export async function POST(req: NextRequest) {
  const authHeader = req.headers.get('authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const token = authHeader.replace('Bearer ', '')
  const supabaseAdmin = createAdminClient()

  // Verify token
  const {
    data: { user },
    error: userError,
  } = await supabaseAdmin.auth.getUser(token)
  if (userError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: {
    messages: Message[]
    sessionId: string
    context?: { label: string; key: string } | null
    messageCount?: number
  }

  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }

  const { messages, sessionId, context, messageCount = 0 } = body

  // Check subscription — gate after 3 messages
  const { data: sub } = await supabaseAdmin
    .from('subscriptions')
    .select('*')
    .eq('user_id', user.id)
    .single()

  if (messageCount >= 3 && !isSubscriptionActive(sub)) {
    return NextResponse.json({ error: 'subscription_required' }, { status: 402 })
  }

  // Get lead profile
  const { data: lead } = await supabaseAdmin
    .from('leads')
    .select('name, org, role')
    .eq('user_id', user.id)
    .single()

  const leadData = lead || { name: 'there', org: 'your practice', role: 'Revenue Cycle' }

  // RAG — search knowledge base using last user message
  const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user')
  const ragQuery = lastUserMessage?.content || ''
  const relevantKnowledge = ragQuery
    ? await searchKnowledge(supabaseAdmin, ragQuery)
    : []

  // Memory — recent session summaries
  const memoryContext = await getRecentSessionSummary(supabaseAdmin, user.id, sessionId)

  // Tier
  const tier = sub?.tier ?? (isSubscriptionActive(sub) ? 'trialing' : 'free')

  // Build system prompt
  const systemPrompt = buildSystemPrompt({
    lead: leadData,
    context: context ?? null,
    tier,
    relevantKnowledge,
    memoryContext,
  })

  // Build API messages
  const apiMessages = messages.map((m) => ({
    role: m.role as 'user' | 'assistant',
    content: m.content,
  }))

  // Call Claude
  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 800,
    system: systemPrompt,
    messages: apiMessages,
  })

  const textBlock = response.content.find((c) => c.type === 'text')
  const text = textBlock?.type === 'text' ? textBlock.text : ''
  const isAppealLetter = text.trimStart().startsWith('APPEAL LETTER:')

  // Persist updated session
  const updatedMessages: Message[] = [
    ...messages,
    {
      role: 'assistant',
      content: text,
      timestamp: new Date().toISOString(),
      isAppealLetter,
    },
  ]

  await supabaseAdmin.from('chat_sessions').upsert({
    id: sessionId,
    user_id: user.id,
    context: context?.label ?? null,
    messages: updatedMessages,
    updated_at: new Date().toISOString(),
  })

  return NextResponse.json({ text, isAppealLetter })
}
