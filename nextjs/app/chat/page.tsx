import { redirect } from 'next/navigation'
import { createServerClient } from '@/lib/supabase-server'
import { createAdminClient } from '@/lib/supabase-server'
import ChatShell from '@/components/ChatShell'
import type { Subscription } from '@/lib/supabase'

export const metadata = { title: 'Chat — CodeMed AI' }

export default async function ChatPage() {
  const supabase = createServerClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) redirect('/auth')

  // Fetch subscription server-side so first render has it
  const supabaseAdmin = createAdminClient()
  const { data: sub } = await supabaseAdmin
    .from('subscriptions')
    .select('*')
    .eq('user_id', session.user.id)
    .single()

  return (
    <ChatShell
      userEmail={session.user.email ?? ''}
      initialSubscription={(sub as Subscription) ?? null}
    />
  )
}
