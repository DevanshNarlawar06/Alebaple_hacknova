import { useEffect, useMemo, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Search, Play, Smartphone, BarChart3 } from 'lucide-react'
import { api, ago, onStream } from '../lib/api'
import { StatusPill, ConfBar } from '../components/ui'
import MapView from '../components/MapView'
import ClaimPanel from '../components/ClaimPanel'
import CheckModal from '../components/CheckModal'

const FILTERS = ['ALL', 'VERIFIED', 'CONFLICTING', 'OUTDATED', 'UNVERIFIED']

export default function Console() {
  const [claims, setClaims] = useState([])
  const [alerts, setAlerts] = useState([])
  const [sel, setSel] = useState(null)
  const [filter, setFilter] = useState('ALL')
  const [q, setQ] = useState('')
  const [check, setCheck] = useState(false)
  const [health, setHealth] = useState(null)
  const [filtered, setFiltered] = useState(0)
  const [feed, setFeed] = useState([])
  const [layers, setLayers] = useState({ alerts: true, claims: true })
  const [target, setTarget] = useState(null)

  const load = useCallback(() => {
    api.claims('CURRENT', 200).then(setClaims).catch(() => {})
    api.alerts().then(setAlerts).catch(() => {})
  }, [])
  useEffect(() => {
    load()
    api.health().then(setHealth).catch(() => setHealth({ ok: false }))
    return onStream({
      'claim.verdict': (d) => { load(); setFeed((f) => [{ t: Date.now(), msg: `${d.status} · ${d.claim_text}` }, ...f].slice(0, 6)) },
      'post.filtered': () => setFiltered((n) => n + 1),
      'post.received': (d) => setFeed((f) => [{ t: Date.now(), msg: `Received · ${d.text}` }, ...f].slice(0, 6)),
      'alerts.refreshed': () => api.alerts().then(setAlerts),
    })
  }, [load])

  const shown = useMemo(() => claims.filter((c) =>
    (filter === 'ALL' || c.status === filter) && (!q || c.claim_text.toLowerCase().includes(q.toLowerCase()))), [claims, filter, q])

  const select = (id) => {
    setSel(id)
    const c = claims.find((x) => x.claim_id === id)
    if (c?.latitude != null) setTarget({ lat: c.latitude, lon: c.longitude, zoom: 11 })
  }
  const counts = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f, f === 'ALL' ? claims.length : claims.filter((c) => c.status === f).length])), [claims])

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-line px-4">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold tracking-tight">SachVerify</span>
          <span className="rounded border border-line bg-subtle px-1.5 py-0.5 font-mono text-[10px] text-ink-3">PS-2 · console</span>
        </div>
        <div className="relative w-[380px]">
          <Search size={15} className="absolute left-3 top-2 text-ink-2" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search claims"
            className="w-full rounded border border-line bg-subtle py-1.5 pl-9 pr-3 text-xs outline-none focus:border-accent focus:bg-white" />
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-ghost" onClick={() => api.replay(['pune_flood', 'delhi_quake'])} title="Replay synthetic demo scenarios">
            <Play size={13} /> Replay demo
          </button>
          <span className="flex items-center gap-1.5 text-xs text-ink-2">
            <span className={`h-1.5 w-1.5 rounded-full ${health?.ok ? 'bg-ink-2' : 'bg-st-alert'}`} />
            {health?.ok ? `Live feeds OK · ${health.counts?.evidence ?? 0} evidence` : 'API offline'}
          </span>
          <Link to="/eval" className="p-1.5 text-ink-2 hover:text-ink" title="Evaluation"><BarChart3 size={17} /></Link>
          <Link to="/beacon" className="p-1.5 text-ink-2 hover:text-ink" title="Beacon (phone app)"><Smartphone size={17} /></Link>
          <button className="btn-primary" onClick={() => setCheck(true)}>Check a post</button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="flex w-[360px] shrink-0 flex-col border-r border-line">
          <div className="space-y-2.5 border-b border-line p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium">Stories <span className="font-mono text-xs text-ink-3">({claims.length})</span></span>
              <span className="font-mono text-[11px] text-ink-3">filtered out ({filtered})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button key={f} onClick={() => setFilter(f)} className={`chip ${filter === f ? 'chip-on' : ''}`}>
                  {f === 'ALL' ? 'All' : f[0] + f.slice(1).toLowerCase()} <span className="text-ink-3">{counts[f]}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {shown.map((c) => (
              <button key={c.claim_id} onClick={() => select(c.claim_id)}
                className={`block w-full border-b border-line px-4 py-3.5 text-left hover:bg-subtle ${sel === c.claim_id ? 'border-l-2 border-l-accent bg-subtle' : ''}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs text-ink-2">{c.location_text || c.event_type} · {ago(c.created_at)}</span>
                  <StatusPill status={c.status} small />
                </div>
                <div className="mt-1.5 line-clamp-2 text-[13.5px] font-medium">{c.claim_text}</div>
                <div className="mt-2 flex items-center justify-between font-mono text-[11px] text-ink-3">
                  <span>{c.channel} · {c.language || 'und'}</span><ConfBar value={c.confidence} />
                </div>
              </button>
            ))}
            {!shown.length && (
              <div className="p-6 text-sm text-ink-3">
                No stories yet. Use <b>Replay demo</b> to stream the synthetic Pune / Delhi scenarios, or <b>Check a post</b>.
              </div>
            )}
          </div>
          {feed.length > 0 && (
            <div className="border-t border-line p-3">
              <div className="label mb-1">Live</div>
              {feed.map((f) => <div key={f.t + f.msg} className="truncate font-mono text-[11px] text-ink-3">{f.msg}</div>)}
            </div>
          )}
        </aside>

        <main className="relative flex-1">
          <MapView alerts={alerts} claims={claims} selectedId={sel} onSelect={select} target={target} layers={layers} />
          <div className="absolute left-1/2 top-3 z-[500] flex -translate-x-1/2 rounded border border-line bg-white text-xs">
            {[['alerts', 'Official alerts'], ['claims', 'Claims']].map(([k, label]) => (
              <button key={k} onClick={() => setLayers((l) => ({ ...l, [k]: !l[k] }))}
                className={`px-3 py-1.5 ${layers[k] ? 'text-ink' : 'text-ink-3'} border-r border-line last:border-0`}>
                {layers[k] ? '✓ ' : ''}{label}
              </button>
            ))}
          </div>
          <div className="absolute bottom-4 left-4 z-[500] rounded border border-line bg-white p-3 text-xs">
            <div className="label mb-1.5">Map legend</div>
            {[['#5F7F68', 'Verified'], ['#A88442', 'Conflicting'], ['#A3A3A3', 'Outdated'], ['#6B7A99', 'Unverified']].map(([c, l]) => (
              <div key={l} className="flex items-center gap-2 py-0.5"><span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />{l}</div>
            ))}
            <div className="flex items-center gap-2 py-0.5"><span className="h-2.5 w-3 border border-dashed border-ink-2" />Official alert area ({alerts.length})</div>
          </div>
        </main>

        <aside className="w-[440px] shrink-0 border-l border-line">
          <ClaimPanel claimId={sel} />
        </aside>
      </div>
      {check && <CheckModal onClose={() => setCheck(false)} onDone={(r) => { load(); if (r.claim_id && r.status) setSel(r.claim_id) }} />}
    </div>
  )
}
