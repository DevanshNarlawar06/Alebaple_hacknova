import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmtTime } from '../lib/api'

const S = ['VERIFIED', 'CONFLICTING', 'OUTDATED', 'UNVERIFIED']

export default function Eval() {
  const [d, setD] = useState(null)
  useEffect(() => { api.evalLatest().then(setD) }, [])
  if (!d) return <div className="p-8 text-sm text-ink-3">Loading…</div>
  if (!d.available) return <div className="p-8 text-sm text-ink-3">No evaluation run yet. Run <code>scripts/run_eval.py</code>.</div>
  const m = d.metrics
  const max = Math.max(1, ...S.flatMap((e) => S.map((p) => d.confusion[e][p])))
  const cases = d.config?.cases || []
  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Evaluation</h1>
        <Link to="/" className="text-sm text-accent">← Console</Link>
      </div>
      <p className="mt-1 font-mono text-xs text-ink-3">run {d.id} · {fmtTime(d.created_at)} · split {d.split} · n = {m.n}</p>
      {m.includes_unreviewed && (
        <p className="mt-3 rounded border border-line bg-subtle p-3 text-xs text-ink-2">
          Development run: includes cases not yet human-reviewed, and these are the cases the rules were tuned on. Not a held-out score.
        </p>
      )}
      <div className="mt-6 grid grid-cols-4 gap-3">
        {[['Macro-F1', m.macro_f1], ['Accuracy', m.accuracy], ['Critical errors', m.critical_errors], ['Median latency', `${m.median_latency_s}s`]].map(([k, v]) => (
          <div key={k} className="card p-4"><div className="label">{k}</div><div className="mt-2 font-mono text-2xl">{v}</div></div>
        ))}
      </div>
      <div className="mt-6 grid grid-cols-2 gap-6">
        <div className="card p-5">
          <div className="label mb-3">Confusion matrix (rows = expected)</div>
          <table className="w-full text-center font-mono text-xs">
            <thead><tr><th /> {S.map((s) => <th key={s} className="pb-2 font-normal text-ink-3">{s.slice(0, 4)}</th>)}</tr></thead>
            <tbody>{S.map((e) => (
              <tr key={e}><td className="pr-2 text-right text-ink-3">{e.slice(0, 4)}</td>
                {S.map((p) => { const v = d.confusion[e][p]; return (
                  <td key={p} className="p-0.5"><div className="rounded py-3" style={{ background: `rgba(15,118,110,${v / max * 0.55})`, color: v / max > 0.5 ? '#fff' : '#171717', outline: e === p ? '1px solid #171717' : 'none' }}>{v}</div></td>) })}
              </tr>))}</tbody>
          </table>
        </div>
        <div className="card p-5">
          <div className="label mb-3">Per status</div>
          <table className="w-full font-mono text-xs">
            <thead className="text-ink-3"><tr><th className="text-left font-normal">status</th><th className="font-normal">P</th><th className="font-normal">R</th><th className="font-normal">F1</th><th className="font-normal">n</th></tr></thead>
            <tbody>{S.map((s) => <tr key={s} className="border-t border-line"><td className="py-2">{s.toLowerCase()}</td>
              {['precision', 'recall', 'f1', 'support'].map((k) => <td key={k} className="text-center">{m.per_status[s][k]}</td>)}</tr>)}</tbody>
          </table>
          <div className="label mb-2 mt-5">Failure categories</div>
          {Object.keys(d.failures || {}).length === 0 ? <p className="text-xs text-ink-3">None in this run.</p> :
            Object.entries(d.failures).map(([k, v]) => <div key={k} className="flex justify-between text-xs"><span>{k}</span><span className="font-mono">{v}</span></div>)}
        </div>
      </div>
      <div className="card mt-6 p-5">
        <div className="label mb-3">Cases</div>
        <table className="w-full text-xs">
          <thead className="text-left text-ink-3"><tr><th className="font-normal">case</th><th className="font-normal">context</th><th className="font-normal">expected</th><th className="font-normal">predicted</th><th className="font-normal">review</th><th className="font-normal">failure</th></tr></thead>
          <tbody>{cases.map((c) => <tr key={c.case_id} className="border-t border-line"><td className="py-2 font-mono">{c.case_id}</td><td>{c.context}</td><td>{c.expected}</td><td>{c.predicted}</td><td className="font-mono">{c.review}</td><td className="text-ink-3">{c.failure || '—'}</td></tr>)}</tbody>
        </table>
        <p className="mt-3 font-mono text-[11px] text-ink-3">All numbers produced by scripts/run_eval.py — not hand-entered.</p>
      </div>
    </div>
  )
}
