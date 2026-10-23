const j = async (r) => {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}
export const api = {
  health: () => fetch('/api/health').then(j),
  claims: (ctx = 'CURRENT', limit = 100) => fetch(`/api/claims?context=${ctx}&limit=${limit}`).then(j),
  claim: (id) => fetch(`/api/claims/${id}`).then(j),
  alerts: () => fetch('/api/alerts?active=true&limit=300').then(j),
  check: (body, persist = true) =>
    fetch(persist ? '/api/tipline' : '/api/claims/check', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(j),
  replay: (scenarios) =>
    fetch('/api/admin/replay', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenarios, seconds_per_minute: 1.0 }),
    }).then(j),
  beacon: (lat, lon, r = 10) => fetch(`/api/beacon/status?lat=${lat}&lon=${lon}&radius_km=${r}`).then(j),
  evalLatest: () => fetch('/api/eval/latest').then(j),
}

export function onStream(handlers) {
  const es = new EventSource('/api/stream')
  for (const [type, fn] of Object.entries(handlers)) es.addEventListener(type, (e) => fn(JSON.parse(e.data)))
  return () => es.close()
}

export function ago(iso) {
  if (!iso) return ''
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 0) return 'upcoming'
  if (s < 90) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  const d = Math.round(s / 86400)
  return d < 400 ? `${d} d ago` : `${(d / 365).toFixed(1)} y ago`
}

export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—')
