import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase-server'
import { getStripe, getOrCreateStripeCustomer, PRICE_IDS, type TierKey } from '@/lib/stripe'

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

  let body: { tier: TierKey }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
  }

  const { tier } = body
  const priceId = PRICE_IDS[tier]
  if (!priceId) {
    return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })
  }

  const stripe = getStripe()
  const email = user.email!
  const customerId = await getOrCreateStripeCustomer(stripe, email, user.id)

  // Check founding member count
  const { count } = await supabaseAdmin
    .from('founding_members')
    .select('*', { count: 'exact', head: true })

  const isFoundingMember = (count ?? 0) < 5

  // Build checkout session
  const origin = req.headers.get('origin') || 'https://codemedgroup.com'

  const sessionParams: Parameters<typeof stripe.checkout.sessions.create>[0] = {
    customer: customerId,
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    subscription_data: {
      trial_period_days: 14,
      metadata: { supabase_user_id: user.id, tier },
    },
    metadata: { supabase_user_id: user.id, tier },
    success_url: `${origin}/chat?success=true`,
    cancel_url: `${origin}/pricing`,
    allow_promotion_codes: true,
  }

  if (isFoundingMember) {
    sessionParams.discounts = [{ coupon: 'FOUNDING' }]
  }

  const session = await stripe.checkout.sessions.create(sessionParams)

  return NextResponse.json({ url: session.url })
}
