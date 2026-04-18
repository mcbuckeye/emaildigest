import { useMemo } from 'react'

/** Minimal visual cron builder. Presents common presets + manual override. */
interface Props {
  value: string
  onChange: (cron: string) => void
}

const PRESETS: Array<{ label: string; cron: string }> = [
  { label: 'Daily at 9:00', cron: '0 9 * * *' },
  { label: 'Weekdays at 8:00', cron: '0 8 * * 1-5' },
  { label: 'Monday 9:00', cron: '0 9 * * 1' },
  { label: 'Sunday 9:00', cron: '0 9 * * 0' },
  { label: 'Monthly — 1st at 9:00', cron: '0 9 1 * *' },
]

export default function CronBuilder({ value, onChange }: Props) {
  const [minute, hour, dom, month, dow] = useMemo(() => value.split(/\s+/), [value])

  const set = (idx: number, next: string) => {
    const parts = value.split(/\s+/)
    parts[idx] = next
    onChange(parts.join(' '))
  }

  const presetMatch = PRESETS.find((p) => p.cron === value)

  return (
    <div>
      <div className="input-group">
        <label>Preset</label>
        <select
          aria-label="preset"
          value={presetMatch ? presetMatch.cron : 'custom'}
          onChange={(e) => {
            const v = e.target.value
            if (v === 'custom') return
            onChange(v)
          }}
        >
          {PRESETS.map((p) => (
            <option key={p.cron} value={p.cron}>{p.label}</option>
          ))}
          <option value="custom">Custom…</option>
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
        <Field label="minute" value={minute} onChange={(v) => set(0, v)} />
        <Field label="hour" value={hour} onChange={(v) => set(1, v)} />
        <Field label="day-of-month" value={dom} onChange={(v) => set(2, v)} />
        <Field label="month" value={month} onChange={(v) => set(3, v)} />
        <Field label="day-of-week" value={dow} onChange={(v) => set(4, v)} />
      </div>
      <p className="text-muted" style={{ fontSize: 12 }}>
        Current: <code>{value}</code>
      </p>
    </div>
  )
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label style={{ fontSize: 12 }}>
      {label}
      <input
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: '100%' }}
      />
    </label>
  )
}
