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

  // Check if lead already exists
  const { data: existing } = await supabaseAdmin
    .from('leads')
    .select('id')
    .eq('user_id', user.id)
    .single()

  if (existing) {
    return NextResponse.json({ id: existing.id, exists: true })
  }

  // Create new lead
  let body: { name: string; org: string; role: string; email?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { name, org, role, email } = body
  if (!name || !org || !role) {
    return NextResponse.json({ error: 'name, org, and role are required' }, { status: 400 })
  }

  const { data: lead, error } = await supabaseAdmin
    .from('leads')
    .insert({
      user_id: user.id,
      name: name.trim(),
      org: org.trim(),
      role: role.trim(),
      email: email || user.email || null,
    })
    .select('id')
    .single()

  if (error) {
    console.error('Lead insert error:', error)
    return NextResponse.json({ error: 'Failed to create lead' }, { status: 500 })
  }

  return NextResponse.json({ id: lead.id, exists: false })
}

export async function GET(req: NextRequest) {
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

  const { data: lead } = await supabaseAdmin
    .from('leads')
    .select('*')
    .eq('user_id', user.id)
    .single()

  return NextResponse.json({ lead })
}
