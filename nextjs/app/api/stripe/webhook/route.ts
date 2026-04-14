import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'
import { createAdminClient } from '@/lib/supabase-server'
import { getStripe } from '@/lib/stripe'

export async function POST(req: NextRequest) {
  const body = await req.text()
  const sig = req.headers.get('stripe-signature')

  if (!sig) {
    return NextResponse.json({ error: 'Missing stripe-signature' }, { status: 400 })
  }

  const stripe = getStripe()
  let event: Stripe.Event

  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!)
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    console.error('Webhook signature error:', message)
    return NextResponse.json({ error: `Webhook Error: ${message}` }, { status: 400 })
  }

  const supabaseAdmin = createAdminClient()

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.Checkout.Session
      const userId = session.metadata?.supabase_user_id
      const tier = session.metadata?.tier as 'starter' | 'growth' | 'enterprise'

      if (!userId || !tier) break

      // Check founding member count before inserting subscription
      const { count } = await supabaseAdmin
        .from('founding_members')
        .select('*', { count: 'exact', head: true })

      const subscriptionId = session.subscription as string

      // Fetch subscription details
      const sub = await stripe.subscriptions.retrieve(subscriptionId)

      await supabaseAdmin.from('subscriptions').upsert({
        user_id: userId,
        stripe_customer_id: session.customer as string,
        stripe_subscription_id: subscriptionId,
        tier,
        status: sub.status as 'trialing' | 'active' | 'past_due' | 'canceled',
        trial_start: sub.trial_start ? new Date(sub.trial_start * 1000).toISOString() : null,
        trial_end: sub.trial_end ? new Date(sub.trial_end * 1000).toISOString() : null,
        current_period_end: new Date(sub.current_period_end * 1000).toISOString(),
        updated_at: new Date().toISOString(),
      })

      // Add founding member if eligible
      if ((count ?? 0) < 5) {
        await supabaseAdmin.from('founding_members').insert({ user_id: userId })
      }

      break
    }

    case 'customer.subscription.updated': {
      const sub = event.data.object as Stripe.Subscription
      const userId = sub.metadata?.supabase_user_id

      if (!userId) {
        // Try to find user by stripe_subscription_id
        const { data: existing } = await supabaseAdmin
          .from('subscriptions')
          .select('user_id')
          .eq('stripe_subscription_id', sub.id)
          .single()

        if (existing) {
          await supabaseAdmin
            .from('subscriptions')
            .update({
              status: sub.status as 'trialing' | 'active' | 'past_due' | 'canceled',
              current_period_end: new Date(sub.current_period_end * 1000).toISOString(),
              trial_end: sub.trial_end ? new Date(sub.trial_end * 1000).toISOString() : null,
              updated_at: new Date().toISOString(),
            })
            .eq('stripe_subscription_id', sub.id)
        }
      } else {
        await supabaseAdmin
          .from('subscriptions')
          .update({
            status: sub.status as 'trialing' | 'active' | 'past_due' | 'canceled',
            current_period_end: new Date(sub.current_period_end * 1000).toISOString(),
            trial_end: sub.trial_end ? new Date(sub.trial_end * 1000).toISOString() : null,
            updated_at: new Date().toISOString(),
          })
          .eq('user_id', userId)
      }

      break
    }

    case 'customer.subscription.deleted': {
      const sub = event.data.object as Stripe.Subscription

      await supabaseAdmin
        .from('subscriptions')
        .update({
          status: 'canceled',
          updated_at: new Date().toISOString(),
        })
        .eq('stripe_subscription_id', sub.id)

      break
    }

    default:
      // Unhandled event type — not an error
      break
  }

  return NextResponse.json({ received: true })
}
