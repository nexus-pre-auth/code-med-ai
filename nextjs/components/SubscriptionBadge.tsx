'use client'

import type { Subscription } from '@/lib/supabase'
import { isSubscriptionActive } from '@/lib/supabase'

interface Props {
  subscription: Subscription | null
}

export default function SubscriptionBadge({ subscription }: Props) {
  if (!subscription) {
    return <span className="badge badge-free">Free</span>
  }

  const active = isSubscriptionActive(subscription)

  if (!active) {
    return <span className="badge badge-free">Expired</span>
  }

  if (subscription.status === 'trialing') {
    const end = subscription.trial_end ? new Date(subscription.trial_end) : null
    const daysLeft = end
      ? Math.max(0, Math.ceil((end.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
      : 0
    return (
      <span className="badge badge-trial">
        Trial · {daysLeft}d left
      </span>
    )
  }

  const tierClass =
    subscription.tier === 'enterprise'
      ? 'badge-enterprise'
      : subscription.tier === 'growth'
      ? 'badge-growth'
      : 'badge-starter'

  const tierLabel =
    subscription.tier === 'enterprise'
      ? 'Enterprise'
      : subscription.tier === 'growth'
      ? 'Growth'
      : 'Starter'

  return <span className={`badge ${tierClass}`}>{tierLabel}</span>
}
