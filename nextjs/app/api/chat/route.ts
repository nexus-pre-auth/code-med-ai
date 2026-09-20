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
  }

  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }

  const { messages, sessionId, context } = body

  if (!Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: 'messages required' }, { status: 400 })
  }

  // Derive count server-side — never trust client-supplied messageCount
  const userMessageCount = messages.filter((m) => m.role === 'user').length

  const { data: sub } = await supabaseAdmin
    .from('subscriptions')
    .select('*')
    .eq('user_id', user.id)
    .single()

  if (userMessageCount >= 3 && !isSubscriptionActive(sub)) {
    return NextResponse.json({ error: 'subscription_required' }, { status: 402 })
  }

  // Validate session ownership before we write to it
  if (sessionId) {
    const { data: existing } = await supabaseAdmin
      .from('chat_sessions')
      .select('user_id')
      .eq('id', sessionId)
      .single()
    if (existing && existing.user_id !== user.id) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
    }
  }

  const { data: lead } = await supabaseAdmin
    .from('leads')
    .select('name, org, role')
    .eq('user_id', user.id)
    .single()

  const leadData = lead || { name: 'there', org: 'your practice', role: 'Revenue Cycle' }

  const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user')
  const ragQuery = lastUserMessage?.content || ''
  const relevantKnowledge = ragQuery ? await searchKnowledge(supabaseAdmin, ragQuery) : []

  const memoryContext = await getRecentSessionSummary(supabaseAdmin, user.id, sessionId)

  const tier = sub?.tier ?? (isSubscriptionActive(sub) ? 'trialing' : 'free')

  const systemPrompt = buildSystemPrompt({
    lead: leadData,
    context: context ?? null,
    tier,
    relevantKnowledge,
    memoryContext,
  })

  const apiMessages = messages
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content }))

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      let fullText = ''

      try {
        const claudeStream = anthropic.messages.stream({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 800,
          system: systemPrompt,
          messages: apiMessages,
        })

        for await (const event of claudeStream) {
          if (
            event.type === 'content_block_delta' &&
            event.delta.type === 'text_delta'
          ) {
            const chunk = event.delta.text
            fullText += chunk
            controller.enqueue(encoder.encode(chunk))
          }
        }

        const isAppealLetter = fullText.trimStart().startsWith('APPEAL LETTER:')

        // Persist session after stream completes
        const updatedMessages: Message[] = [
          ...messages,
          {
            role: 'assistant',
            content: fullText,
            timestamp: new Date().toISOString(),
            isAppealLetter,
          },
        ]

        try {
          await supabaseAdmin.from('chat_sessions').upsert({
            id: sessionId,
            user_id: user.id,
            context: context?.label ?? null,
            messages: updatedMessages,
            updated_at: new Date().toISOString(),
          })
        } catch (dbErr) {
          console.error('Session upsert failed:', dbErr)
        }

        // Sentinel line signals end of stream to client
        controller.enqueue(
          encoder.encode(`\n{"__done":true,"isAppealLetter":${isAppealLetter}}`)
        )
      } catch (err) {
        console.error('Claude stream error:', err)
        controller.enqueue(encoder.encode('\n{"__done":true,"isAppealLetter":false,"error":true}'))
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
