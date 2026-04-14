'use client'

import { TOPIC_CHIPS, type TopicKey } from '@/lib/prompts'

interface Props {
  onSelect: (key: TopicKey, label: string) => void
  disabled?: boolean
  selected?: TopicKey | null
}

export default function ChipRow({ onSelect, disabled = false, selected = null }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        justifyContent: 'center',
        padding: '4px 0 8px',
      }}
    >
      {TOPIC_CHIPS.map((chip) => (
        <button
          key={chip.key}
          className="chip"
          disabled={disabled || selected !== null}
          onClick={() => onSelect(chip.key, chip.label)}
          style={
            selected === chip.key
              ? {
                  borderColor: 'var(--green-border)',
                  background: 'var(--green-glow)',
                  color: 'var(--green)',
                }
              : undefined
          }
        >
          <span>{chip.icon}</span>
          <span>{chip.label}</span>
        </button>
      ))}
    </div>
  )
}
