import { useEffect, useState } from 'react'
import { api, ago, fmtTime } from '../lib/api'
import { StatusPill, Tag, ConfBar, PropositionRow, EvidenceItem } from './ui'

export default function ClaimPanel({ claimId }) {
  const [data, setData] = useState(null)
  const [ctx, setCtx] = useState('CURRENT')
  useEffect(() => {
    if (!claimId) return
    setData(null)
    api.claim(claimId).then((d) => {
      setData(d)
      if (!d.latest.CURRENT && d.latest.HISTORICAL) setCtx('HISTORICAL')
    })
  }, [claimId])
  if (!claimId) return <div className="p-6 text-sm text-ink-3">Select a story to see its evidence.</div>
  if (!data) return <div className="p-6 text-sm text-ink-3">Loading…</div>
  const r = data.latest[ctx] || data.latest.CURRENT || data.latest.HISTORICAL
  if (!r) return <div className="p-6 text-sm text-ink-3">No verdict yet.</div>
  const contexts = Object.keys(data.latest)
  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="border-b border-line p-5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-ink-3">{r.claim_id}</span>
          <div className="flex rounded border border-line bg-subtle p-0.5 text-xs">
            {['CURRENT', 'HISTORICAL'].map((c) => (
              <button key={c} disabled={!data.latest[c]} onClick={() => setCtx(c)}
                className={`rounded-sm px-2.5 py-1 ${ctx === c ? 'border border-line bg-white text-ink' : 'text-ink-3'} disabled:opacity-40`}>
                {c === 'CURRENT' ? 'Current' : 'Historical'}
              </button>
            ))}
          </div>
        </div>
        <h2 className="mt-3 text-lg font-semibold leading-snug">{r.claim_text}</h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <StatusPill status={r.status} />
          <Tag>{(r.verification_subtype || '').replace(/_/g, ' ').toLowerCase()}</Tag>
          <span className="ml-auto"><ConfBar value={r.confidence} /></span>
        </div>
        {contexts.length > 1 && data.latest.HISTORICAL && data.latest.CURRENT &&
          data.latest.HISTORICAL.status !== data.latest.CURRENT.status && (
          <p className="mt-2 text-[11.5px] text-ink-3">
            Historical: {data.latest.HISTORICAL.status.toLowerCase()} · Current: {data.latest.CURRENT.status.toLowerCase()} — true when posted, no longer current.
          </p>
        )}
        <div className="mt-2 font-mono text-[11px] text-ink-3">
          posted {fmtTime(r.claim_time)} · {r.language || 'und'} · {r.hazard}
          {r.geographic_analysis?.resolved?.display ? ` · ${r.geographic_analysis.resolved.display.split(',').slice(0, 2).join(',')}` : ''}
        </div>
      </div>

      <section className="border-b border-line p-5">
        <div className="label mb-3">What's being claimed</div>
        <div className="space-y-2">{r.atomic_propositions.map((p) => <PropositionRow key={p.id} p={p} />)}</div>
      </section>

      <section className="border-b border-line p-5">
        <div className="mb-3 flex items-baseline gap-2"><span className="text-sm font-medium">Supports</span>
          <span className="font-mono text-xs text-ink-3">({r.supporting_evidence.length})</span></div>
        <div className="space-y-2">
          {r.supporting_evidence.slice(0, 6).map((e, i) => <EvidenceItem key={e.evidence_id + i} e={e} />)}
          {!r.supporting_evidence.length && <p className="text-xs text-ink-3">No supporting evidence found.</p>}
        </div>
        <div className="mb-3 mt-5 flex items-baseline gap-2"><span className="text-sm font-medium">Contradicts</span>
          <span className="font-mono text-xs text-ink-3">({r.contradicting_evidence.length})</span></div>
        <div className="space-y-2">
          {r.contradicting_evidence.slice(0, 6).map((e, i) => <EvidenceItem key={e.evidence_id + i} e={e} />)}
          {!r.contradicting_evidence.length && <p className="text-xs text-ink-3">No positive contradicting evidence. (Absence of evidence is not treated as contradiction.)</p>}
        </div>
        {r.superseded_or_stale_evidence?.length > 0 && (
          <>
            <div className="mb-3 mt-5 text-sm font-medium">No longer current</div>
            <div className="space-y-2">{r.superseded_or_stale_evidence.slice(0, 4).map((e, i) => <EvidenceItem key={e.evidence_id + 's' + i} e={e} />)}</div>
          </>
        )}
      </section>

      <section className="border-b border-line p-5">
        <div className="label mb-3">Time</div>
        <dl className="grid grid-cols-2 gap-y-1.5 font-mono text-[11.5px]">
          <dt className="text-ink-3">claim posted</dt><dd>{fmtTime(r.temporal_analysis?.claim_time)}</dd>
          <dt className="text-ink-3">event (claimed)</dt><dd>{r.temporal_analysis?.event_time || '—'}</dd>
          <dt className="text-ink-3">verified at</dt><dd>{fmtTime(r.temporal_analysis?.verification_time)}</dd>
          <dt className="text-ink-3">bound event</dt><dd>{r.temporal_analysis?.bound_event || '—'}</dd>
        </dl>
      </section>

      <section className="p-5">
        <div className="label mb-2">Why this status</div>
        <pre className="whitespace-pre-wrap font-sans text-[12.5px] leading-relaxed text-ink-2">{r.explanation}</pre>
        {r.uncertainty?.length > 0 && (
          <>
            <div className="label mb-1 mt-4">Uncertainty</div>
            <ul className="list-disc space-y-1 pl-4 text-[12px] text-ink-3">{r.uncertainty.map((u, i) => <li key={i}>{u}</li>)}</ul>
          </>
        )}
        <div className="label mb-1 mt-4">Verdict history</div>
        <ul className="space-y-1 font-mono text-[11px] text-ink-3">
          {data.history.map((h) => <li key={h.verification_context + h.version}>v{h.version} · {h.verification_context.toLowerCase()} · {h.status.toLowerCase()} · {ago(h.created_at)}</li>)}
        </ul>
      </section>
    </div>
  )
}
