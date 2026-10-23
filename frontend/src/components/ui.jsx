import { Check, X, HelpCircle, RotateCcw, Minus, ExternalLink } from 'lucide-react'
import { ago } from '../lib/api'

export const STATUS = {
  VERIFIED: { label: 'Verified', dot: 'bg-st-verified', hex: '#5F7F68' },
  CONFLICTING: { label: 'Conflicting', dot: 'bg-st-conflicting', hex: '#A88442' },
  OUTDATED: { label: 'Outdated', dot: 'bg-st-outdated', hex: '#A3A3A3' },
  UNVERIFIED: { label: 'Unverified', dot: 'bg-st-unverified', hex: '#6B7A99' },
}

export function StatusPill({ status, small }) {
  const s = STATUS[status] || { label: status || 'Not a claim', dot: 'bg-ink-3' }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border border-line bg-white ${small ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'} text-ink`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  )
}

export function Tag({ children }) {
  return <span className="rounded border border-line px-1.5 py-0.5 font-mono text-[10.5px] text-ink-2">{children}</span>
}

export function ConfBar({ value }) {
  const v = Math.max(0, Math.min(1, value || 0))
  const label = v >= 0.6 ? 'High' : v >= 0.3 ? 'Medium' : 'Low'
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[11px] text-ink-3">
      {label.toUpperCase()}
      <span className="h-1 w-16 rounded bg-line"><span className="block h-1 rounded bg-ink" style={{ width: `${v * 100}%` }} /></span>
    </span>
  )
}

const STATE_ICON = {
  SUPPORTED: [Check, 'text-st-verified'], CONTRADICTED: [X, 'text-st-conflicting'], DISPUTED: [X, 'text-st-conflicting'],
  SUPERSEDED: [RotateCcw, 'text-ink-3'], UNVERIFIED: [HelpCircle, 'text-st-unverified'],
  SUBJECTIVE: [Minus, 'text-ink-3'], NON_FACTUAL: [Minus, 'text-ink-3'],
}

export function PropositionRow({ p }) {
  const [Icon, cls] = STATE_ICON[p.state] || [HelpCircle, 'text-ink-3']
  const excluded = p.state === 'SUBJECTIVE' || p.state === 'NON_FACTUAL'
  return (
    <div className={`flex items-start gap-3 rounded-md border border-line px-3 py-2.5 ${excluded ? 'bg-subtle' : ''}`}>
      <Icon size={15} className={`mt-0.5 shrink-0 ${cls}`} />
      <div className="min-w-0 flex-1">
        <div className={`text-[13px] ${excluded ? 'text-ink-3' : 'text-ink'}`}>{p.text}</div>
        {p.superseding?.length > 0 && <div className="mt-1 text-[11px] text-ink-3">{p.superseding[0]}</div>}
      </div>
      <div className="flex shrink-0 gap-1">
        <Tag>{p.materiality || '—'}</Tag>
        <Tag>{excluded ? `${p.factuality.toLowerCase()} · excluded` : p.state.toLowerCase()}</Tag>
      </div>
    </div>
  )
}

const LAYER = { official: 'Official', sensor: 'Sensor', local_news: 'Local news', national_global: 'National', social: 'Post', humanitarian: 'Humanitarian' }

export function EvidenceItem({ e }) {
  return (
    <div className="rounded-md border border-line p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Tag>{LAYER[e.layer] || e.layer || 'Source'}</Tag>
          <span className="truncate text-xs font-medium text-ink">{e.source}</span>
          {e.credibility_tier && <span className="font-mono text-[10px] text-ink-3">tier {e.credibility_tier}</span>}
          {e.is_synthetic && <Tag>synthetic</Tag>}
        </div>
        <span className="shrink-0 font-mono text-[11px] text-ink-3">{ago(e.published_at)}</span>
      </div>
      <p className="mt-2 border-l-2 border-line pl-2.5 text-[12.5px] leading-relaxed text-ink-2 line-clamp-3">
        {e.interpretation || e.excerpt}
      </p>
      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-ink-3">
        <span className="truncate">{[e.geo_basis, e.temporal_relation?.replace(/_/g, ' '), e.reason].filter(Boolean).join(' · ')}</span>
        {e.url && (
          <a href={e.url} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-1 text-accent hover:underline">
            Open source <ExternalLink size={11} />
          </a>
        )}
      </div>
    </div>
  )
}
