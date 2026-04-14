import { redirect } from 'next/navigation'
import { createServerClient } from '@/lib/supabase-server'
import KnowledgeAdmin from '@/components/KnowledgeAdmin'

export const metadata = { title: 'Admin — CodeMed' }

export default async function AdminPage() {
  const supabase = createServerClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) redirect('/auth')

  return <KnowledgeAdmin token={session.access_token} />
}
