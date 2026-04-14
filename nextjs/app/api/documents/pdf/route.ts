import { NextRequest, NextResponse } from 'next/server'
import { renderToBuffer } from '@react-pdf/renderer'
import { createAdminClient } from '@/lib/supabase-server'
import { AppealLetterDocument } from '@/lib/pdf'

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

  let body: {
    content: string
    title: string
    payer?: string
    drug?: string
    sessionId?: string
  }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { content, title, payer, drug, sessionId } = body
  if (!content || !title) {
    return NextResponse.json({ error: 'content and title are required' }, { status: 400 })
  }

  const date = new Date().toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  // Generate PDF buffer
  const pdfBuffer = await renderToBuffer(
    AppealLetterDocument({ content, date }) as React.ReactElement
  )

  // Upload to Supabase Storage
  const timestamp = Date.now()
  const filePath = `${user.id}/appeal-${timestamp}.pdf`

  const { error: uploadError } = await supabaseAdmin.storage
    .from('documents')
    .upload(filePath, pdfBuffer, {
      contentType: 'application/pdf',
      upsert: false,
    })

  if (uploadError) {
    console.error('PDF upload error:', uploadError)
    return NextResponse.json({ error: 'Failed to upload PDF' }, { status: 500 })
  }

  const { data: urlData } = supabaseAdmin.storage
    .from('documents')
    .getPublicUrl(filePath)

  const pdfUrl = urlData.publicUrl

  // Save document record
  const { data: doc, error: docError } = await supabaseAdmin
    .from('documents')
    .insert({
      user_id: user.id,
      session_id: sessionId || null,
      type: 'appeal_letter',
      title: title.trim(),
      content,
      payer: payer || null,
      drug: drug || null,
      pdf_url: pdfUrl,
    })
    .select('id')
    .single()

  if (docError) {
    console.error('Document record error:', docError)
    return NextResponse.json({ error: 'Failed to save document record' }, { status: 500 })
  }

  return NextResponse.json({ url: pdfUrl, id: doc.id })
}
