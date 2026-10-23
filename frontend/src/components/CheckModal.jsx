import { useState } from 'react'
import { X } from 'lucide-react'
import { api } from '../lib/api'
import { StatusPill } from './ui'

const STEPS = ['Reading claim', 'Splitting into facts', 'Finding place', 'Searching official alerts', 'Checking sensors', 'Searching local news', 'Deciding']

export default function CheckModal({ onClose, onDone }) {
  const [text, setText] = useState('')
  const [posted, setPosted] = useState('')
  const [place, setPlace] = useState('')
  const [ctx, setCtx] = useState('CURRENT')
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState(null)
  const [err, setErr] = useState(null)
  const submit = async () => {
    setBusy(true); setErr(null); setRes(null)
    try {
      const r = await api.check({ text, posted_at: posted ? new Date(posted).toISOString() : null, place: place || null, verification_context: ctx })
      setRes(r); onDone?.(r)
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }
  return (
    <div className="fixed inset-0 z-[1000] flex items-start justify-center bg-black/20 pt-[10vh]" onClick={onClose}>
      <div className="card w-[640px] max-w-[94vw] p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Check a post</h3>
          <button onClick={onClose} className="text-ink-3 hover:text-ink"><X size={18} /></button>
        </div>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4}
          placeholder="Paste the message, caption or link"
          className="mt-4 w-full rounded border border-line bg-subtle p-3 text-sm outline-none focus:border-accent focus:bg-white" />
        <div className="mt-3 grid grid-cols-3 gap-2">
          <input type="datetime-local" value={posted} onChange={(e) => setPosted(e.target.value)} className="rounded border border-line px-2 py-1.5 text-xs" title="Posted at" />
          <input value={place} onChange={(e) => setPlace(e.target.value)} placeholder="Place (if known)" className="rounded border border-line px-2 py-1.5 text-xs" />
          <div className="flex rounded border border-line bg-subtle p-0.5 text-xs">
            {['CURRENT', 'HISTORICAL'].map((c) => (
              <button key={c} onClick={() => setCtx(c)} className={`flex-1 rounded-sm ${ctx === c ? 'border border-line bg-white' : 'text-ink-3'}`}>
                {c === 'CURRENT' ? 'Current' : 'Historical'}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={!text.trim() || busy} onClick={submit}>{busy ? 'Verifying…' : 'Verify'}</button>
        </div>
        {busy && (
          <ul className="mt-4 space-y-1 font-mono text-[11px] text-ink-3">
            {STEPS.map((s, i) => <li key={s} className="animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>· {s}</li>)}
          </ul>
        )}
        {err && <p className="mt-4 text-xs text-st-alert">{err}</p>}
        {res && (
          <div className="mt-5 rounded-md border border-line p-4">
            {res.checkworthy === false ? (
              <p className="text-sm text-ink-2">Not a checkable claim: {res.triage_reason}</p>
            ) : (
              <>
                <div className="flex items-center gap-2"><StatusPill status={res.status} />
                  <span className="font-mono text-[11px] text-ink-3">{res.verification_subtype?.replace(/_/g, ' ').toLowerCase()}</span></div>
                <p className="mt-2 whitespace-pre-wrap text-[12.5px] text-ink-2">{res.explanation}</p>
                <p className="mt-2 font-mono text-[11px] text-ink-3">{res.supporting_evidence.length} supporting · {res.contradicting_evidence.length} contradicting · {res.latency_s}s</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
