import { useEffect, useRef, useState } from 'react'
import { ShieldCheck, Eye, AlertTriangle, ChevronLeft, Settings, Home, Map as MapIcon, MessageSquare, Bell, BellOff } from 'lucide-react'
import { api, ago, onStream } from '../lib/api'
import { StatusPill, EvidenceItem } from '../components/ui'

const PLACES = {
  'Kothrud, Pune': [18.5074, 73.8077], 'Sinhagad Road, Pune': [18.4745, 73.818], 'Laxmi Nagar, Delhi': [28.6304, 77.2777],
  'Mumbai': [19.076, 72.8777], 'Anantapur, AP': [14.6819, 77.6006],
}

function useAlarm() {
  const ctx = useRef(null)
  const unlock = () => { ctx.current = ctx.current || new (window.AudioContext || window.webkitAudioContext)(); ctx.current.resume() }
  const play = () => {
    if (!ctx.current) return
    const a = ctx.current
    ;[0, 0.35, 0.7].forEach((t, i) => {
      const o = a.createOscillator(); const g = a.createGain()
      o.frequency.value = 660 + i * 110; g.gain.setValueAtTime(0.0001, a.currentTime + t)
      g.gain.exponentialRampToValueAtTime(0.25, a.currentTime + t + 0.03); g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + t + 0.3)
      o.connect(g).connect(a.destination); o.start(a.currentTime + t); o.stop(a.currentTime + t + 0.32)
    })
    navigator.vibrate?.([200, 100, 200])
  }
  return { unlock, play }
}

export default function Beacon() {
  const [place, setPlace] = useState('Kothrud, Pune')
  const [st, setSt] = useState(null)
  const [view, setView] = useState('home')
  const [sound, setSound] = useState(false)
  const [msg, setMsg] = useState('')
  const [checkRes, setCheckRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const last = useRef(null)
  const alarm = useAlarm()
  const [lat, lon] = PLACES[place]

  const refresh = () => api.beacon(lat, lon, 10).then((s) => {
    setSt(s)
    if (s.level === 'RED' && last.current && last.current !== 'RED' && sound) {
      alarm.play()
      if (Notification?.permission === 'granted') new Notification('Beacon: ' + s.reason)
    }
    last.current = s.level
  })
  useEffect(() => { last.current = null; refresh(); const off = onStream({ 'claim.verdict': refresh, 'alerts.refreshed': refresh }); const t = setInterval(refresh, 30000); return () => { off(); clearInterval(t) } }, [place, sound]) // eslint-disable-line

  const enableSound = () => { alarm.unlock(); setSound(true); Notification?.requestPermission?.() }
  const level = st?.level || 'GREEN'
  const hero = {
    GREEN: { Icon: ShieldCheck, title: 'All clear near you', cls: 'border-line' },
    YELLOW: { Icon: Eye, title: 'Watch: reports near you', cls: 'border-line' },
    RED: { Icon: AlertTriangle, title: 'Alert for your area', cls: 'border-ink' },
  }[level]
  const covering = st?.alerts_covering?.[0]

  const doCheck = async () => {
    setBusy(true); setCheckRes(null)
    try { setCheckRes(await api.check({ text: msg, lat, lon })) } finally { setBusy(false) }
  }

  return (
    <div className="flex min-h-screen justify-center bg-subtle">
      <div className="relative flex min-h-screen w-full max-w-[420px] flex-col bg-white sm:border-x sm:border-line">
        <header className="flex items-center justify-between border-b border-line px-4 py-3">
          {view === 'home' ? <span className="flex items-center gap-2 font-semibold"><ShieldCheck size={18} /> Beacon</span>
            : <button onClick={() => setView('home')} className="flex items-center gap-1 text-sm"><ChevronLeft size={16} /> Back</button>}
          <select value={place} onChange={(e) => setPlace(e.target.value)} className="rounded-full border border-line px-3 py-1 text-xs">
            {Object.keys(PLACES).map((p) => <option key={p}>{p}</option>)}
          </select>
          <Settings size={18} className="text-ink-2" />
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto p-4 pb-28">
          {view === 'home' && (
            <>
              <button onClick={sound ? () => setSound(false) : enableSound}
                className="flex w-full items-center justify-between rounded-lg border border-line bg-subtle px-4 py-3 text-sm">
                <span className="flex items-center gap-2">{sound ? <Bell size={16} /> : <BellOff size={16} />} Alert sound {sound ? 'on' : 'off'}</span>
                <span className={`h-5 w-9 rounded-full p-0.5 ${sound ? 'bg-accent' : 'bg-line'}`}><span className={`block h-4 w-4 rounded-full bg-white transition ${sound ? 'translate-x-4' : ''}`} /></span>
              </button>

              <div className={`rounded-xl border p-5 ${hero.cls}`}>
                <div className="flex items-center justify-between">
                  <span className="label flex items-center gap-1.5">
                    <hero.Icon size={14} className={level === 'RED' ? 'text-st-alert' : level === 'YELLOW' ? 'text-st-conflicting' : 'text-st-verified'} />
                    {level === 'RED' ? 'Official / verified alert' : level === 'YELLOW' ? 'Watch' : 'Status'}
                  </span>
                  <span className="label">updated {ago(st?.updated_at)}</span>
                </div>
                <h1 className="mt-3 text-2xl font-semibold">{hero.title}</h1>
                <p className="mt-1 font-mono text-xs text-ink-2">{st?.reason}{covering?.valid_until ? ` · valid until ${new Date(covering.valid_until).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}</p>
                {level === 'RED' && covering && (
                  <p className="mt-3 text-[13px] leading-relaxed text-ink-2 line-clamp-4">{covering.raw_evidence_text}</p>
                )}
                {level !== 'GREEN' && (
                  <div className="mt-4 space-y-2">
                    {level === 'RED' && <button className="btn-primary w-full py-3 text-sm">I'm safe</button>}
                    <button className="btn-ghost w-full py-3 text-sm" onClick={() => setView('why')}>Why this {level === 'RED' ? 'alert' : 'status'}?</button>
                  </div>
                )}
                <p className="mt-4 border-t border-line pt-3 font-mono text-[11px] text-ink-3">{st?.rule}</p>
              </div>

              <section>
                <div className="mb-2 flex justify-between"><span className="label">Nearby updates</span><span className="label">{st?.nearby_claims?.length || 0}</span></div>
                <div className="divide-y divide-line rounded-lg border border-line">
                  {(st?.nearby_claims || []).filter((c) => c.status !== 'CONFLICTING' && c.status !== 'OUTDATED').slice(0, 5).map((c) => (
                    <div key={c.claim_id} className="p-4">
                      <div className="flex items-center justify-between"><StatusPill status={c.status} small />
                        <span className="font-mono text-[11px] text-ink-3">{c.distance_km} km · {ago(c.created_at)}</span></div>
                      <p className="mt-2 text-sm">{c.claim_text}</p>
                    </div>
                  ))}
                  {!st?.nearby_claims?.length && <p className="p-4 text-sm text-ink-3">No reports within 50 km.</p>}
                </div>
              </section>

              {st?.rumour_checks?.length > 0 && (
                <section>
                  <div className="label mb-2">Rumour check</div>
                  {st.rumour_checks.map((c) => (
                    <div key={c.claim_id} className="mb-2 rounded-lg border border-line p-4">
                      <div className="flex items-center justify-between"><StatusPill status={c.status} small /><span className="font-mono text-[11px] text-ink-3">{c.distance_km} km</span></div>
                      <p className="mt-2 text-sm text-ink-2">Viral: “{c.claim_text}”</p>
                      <p className="mt-1 text-sm font-medium">{c.status === 'OUTDATED' ? 'This is old information — not current.' : 'Not confirmed. Official sources say otherwise.'}</p>
                    </div>
                  ))}
                </section>
              )}
            </>
          )}

          {view === 'why' && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Why this {level === 'RED' ? 'alert' : 'status'}?</h2>
              <p className="text-sm text-ink-2">{st?.reason}. Beacon only sounds an alarm for official alerts or verified reports. Social posts alone never trigger it.</p>
              {(st?.alerts_covering || []).concat(st?.alerts_nearby || []).slice(0, 4).map((a) => (
                <EvidenceItem key={a.evidence_id} e={{ evidence_id: a.evidence_id, layer: 'official', source: a.source_name, published_at: a.valid_from, excerpt: a.raw_evidence_text, url: a.source_url, geo_basis: a.distance_km != null ? `${a.distance_km} km` : 'covers your area', is_synthetic: !!a.is_synthetic }} />
              ))}
            </section>
          )}

          {view === 'check' && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Check a message</h2>
              <textarea rows={5} value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Paste a forwarded message or link"
                className="w-full rounded-lg border border-line bg-subtle p-3 text-sm outline-none focus:border-accent" />
              <button className="btn-primary w-full py-3 text-sm" disabled={!msg.trim() || busy} onClick={doCheck}>{busy ? 'Checking…' : 'Check'}</button>
              {busy && <div className="h-0.5 w-full overflow-hidden bg-line"><div className="h-0.5 w-1/3 animate-pulse bg-accent" /></div>}
              {checkRes && (
                <div className="rounded-lg border border-line p-4">
                  {checkRes.checkworthy === false ? <p className="text-sm">Nothing to check here: {checkRes.triage_reason}</p> : (
                    <>
                      <StatusPill status={checkRes.status} />
                      <p className="mt-2 text-base font-medium">{{
                        VERIFIED: 'Confirmed by trusted sources', CONFLICTING: 'Not confirmed — trusted sources say otherwise',
                        OUTDATED: 'Old information — no longer current', UNVERIFIED: 'Not confirmed yet — be careful sharing it',
                      }[checkRes.status]}</p>
                      <p className="mt-2 whitespace-pre-wrap text-xs text-ink-2">{checkRes.explanation}</p>
                    </>
                  )}
                </div>
              )}
            </section>
          )}
        </div>

        {view === 'home' && (
          <button onClick={() => setView('check')} className="btn-primary absolute bottom-20 left-1/2 -translate-x-1/2 rounded-full px-5 py-3 text-sm shadow-sm">
            <MessageSquare size={15} /> Check a message
          </button>
        )}
        <nav className="absolute bottom-0 flex w-full justify-around border-t border-line bg-white py-2 text-[11px]">
          {[['home', Home, 'Home'], ['why', MapIcon, 'Why'], ['check', MessageSquare, 'Check']].map(([k, I, l]) => (
            <button key={k} onClick={() => setView(k)} className={`flex flex-col items-center gap-0.5 ${view === k ? 'text-accent' : 'text-ink-2'}`}><I size={18} />{l}</button>
          ))}
        </nav>
      </div>
    </div>
  )
}
