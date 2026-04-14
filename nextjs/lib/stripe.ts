import Stripe from 'stripe'

let stripeClient: Stripe | null = null

export function getStripe(): Stripe {
  if (!stripeClient) {
    stripeClient = new Stripe(process.env.STRIPE_SECRET_KEY!, {
      apiVersion: '2024-10-28.acacia',
    })
  }
  return stripeClient
}

export const PRICE_IDS = {
  starter: process.env.STRIPE_STARTER_PRICE_ID!,
  growth: process.env.STRIPE_GROWTH_PRICE_ID!,
  enterprise: process.env.STRIPE_ENTERPRISE_PRICE_ID!,
} as const

export type TierKey = keyof typeof PRICE_IDS

export async function getOrCreateStripeCustomer(
  stripe: Stripe,
  email: string,
  userId: string
): Promise<string> {
  const existing = await stripe.customers.list({ email, limit: 1 })
  if (existing.data.length > 0) {
    return existing.data[0].id
  }

  const customer = await stripe.customers.create({
    email,
    metadata: { supabase_user_id: userId },
  })
  return customer.id
}
