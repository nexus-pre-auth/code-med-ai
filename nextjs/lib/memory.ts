import Anthropic from '@anthropic-ai/sdk'
import type { Message } from './supabase'

export async function getRecentSessionSummary(
  supabaseAdmin: ReturnType<typeof import('./supabase-server').createAdminClient>,
  userId: string,
  currentSessionId: string
): Promise<string> {
  const { data } = await supabaseAdmin
    .from('chat_sessions')
    .select('summary, context, updated_at')
    .eq('user_id', userId)
    .neq('id', currentSessionId)
    .not('summary', 'is', null)
    .order('updated_at', { ascending: false })
    .limit(3)

  if (!data?.length) return ''

  return `Recent sessions:\n${data
    .map((s) => `- ${s.context || 'General RCM'}: ${s.summary}`)
    .join('\n')}`
}

export async function generateSessionSummary(
  anthropic: Anthropic,
  messages: Message[]
): Promise<string> {
  if (messages.length < 2) return ''

  const convo = messages
    .slice(-6)
    .map((m) => `${m.role}: ${m.content}`)
    .join('\n')

  try {
    const res = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 80,
      messages: [
        {
          role: 'user',
          content: `Summarize this RCM conversation in one sentence. Focus on the main problem and any resolution. Do not include patient names or member IDs.\n\n${convo}`,
        },
      ],
    })

    const block = res.content[0]
    return block.type === 'text' ? block.text : ''
  } catch (err) {
    console.error('Summary generation error:', err)
    return ''
  }
}
