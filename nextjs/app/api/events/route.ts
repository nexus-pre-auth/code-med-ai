import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase-server'

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

  let body: { lead_id: string; event: string; context?: string; metadata?: Record<string, unknown> }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { lead_id, event, context, metadata } = body
  if (!lead_id || !event) {
    return NextResponse.json({ error: 'lead_id and event are required' }, { status: 400 })
  }

  // Verify lead belongs to user
  const { data: lead } = await supabaseAdmin
    .from('leads')
    .select('id')
    .eq('id', lead_id)
    .eq('user_id', user.id)
    .single()

  if (!lead) {
    return NextResponse.json({ error: 'Lead not found' }, { status: 404 })
  }

  const { error } = await supabaseAdmin.from('events').insert({
    lead_id,
    event,
    context: context || null,
    metadata: metadata || {},
  })

  if (error) {
    console.error('Event insert error:', error)
    return NextResponse.json({ error: 'Failed to log event' }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
