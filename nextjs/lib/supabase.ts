import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

export const createClient = () => createClientComponentClient()

export type Database = {
  public: {
    Tables: {
      leads: {
        Row: {
          id: string
          user_id: string
          name: string
          org: string
          role: string
          email: string | null
          created_at: string
        }
        Insert: Omit<leads['Row'], 'id' | 'created_at'>
        Update: Partial<leads['Insert']>
      }
      subscriptions: {
        Row: {
          id: string
          user_id: string
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          tier: 'starter' | 'growth' | 'enterprise' | null
          status: 'trialing' | 'active' | 'past_due' | 'canceled' | null
          trial_start: string | null
          trial_end: string | null
          current_period_end: string | null
          created_at: string
          updated_at: string
        }
        Insert: Omit<subscriptions['Row'], 'id' | 'created_at' | 'updated_at'>
        Update: Partial<subscriptions['Insert']>
      }
      chat_sessions: {
        Row: {
          id: string
          user_id: string
          context: string | null
          summary: string | null
          messages: Message[]
          created_at: string
          updated_at: string
        }
        Insert: Omit<chat_sessions['Row'], 'id' | 'created_at' | 'updated_at'>
        Update: Partial<chat_sessions['Insert']>
      }
      documents: {
        Row: {
          id: string
          user_id: string
          session_id: string | null
          type: 'appeal_letter' | 'pa_package' | 'roi_report'
          title: string
          content: string
          pdf_url: string | null
          payer: string | null
          drug: string | null
          created_at: string
        }
        Insert: Omit<documents['Row'], 'id' | 'created_at'>
        Update: Partial<documents['Insert']>
      }
      knowledge_base: {
        Row: {
          id: string
          category: string
          title: string
          content: string
          tags: string[]
          source: string
          active: boolean
          embedding: number[] | null
          created_at: string
          updated_at: string
        }
        Insert: Omit<knowledge_base['Row'], 'id' | 'created_at' | 'updated_at'>
        Update: Partial<knowledge_base['Insert']>
      }
    }
  }
}

// Convenience type aliases
type leads = Database['public']['Tables']['leads']
type subscriptions = Database['public']['Tables']['subscriptions']
type chat_sessions = Database['public']['Tables']['chat_sessions']
type documents = Database['public']['Tables']['documents']
type knowledge_base = Database['public']['Tables']['knowledge_base']

export type Lead = leads['Row']
export type Subscription = subscriptions['Row']
export type ChatSession = chat_sessions['Row']
export type Document = documents['Row']
export type KnowledgeEntry = knowledge_base['Row']

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  isAppealLetter?: boolean
}

export function isSubscriptionActive(sub: Subscription | null): boolean {
  if (!sub) return false
  if (sub.status === 'active') return true
  if (sub.status === 'trialing' && sub.trial_end) {
    return new Date(sub.trial_end) > new Date()
  }
  return false
}
