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

  let body: { lead_id: string; email: string; context?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { lead_id, email, context } = body
  if (!lead_id || !email) {
    return NextResponse.json({ error: 'lead_id and email are required' }, { status: 400 })
  }

  // Basic email validation
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: 'Invalid email format' }, { status: 400 })
  }

  const { error } = await supabaseAdmin.from('email_captures').insert({
    lead_id,
    email: email.toLowerCase().trim(),
    context: context || null,
  })

  if (error) {
    console.error('Email capture error:', error)
    return NextResponse.json({ error: 'Failed to capture email' }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
