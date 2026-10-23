import { MapContainer, TileLayer, GeoJSON, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import { useEffect } from 'react'
import 'leaflet/dist/leaflet.css'
import { STATUS } from './ui'

function FlyTo({ target }) {
  const map = useMap()
  useEffect(() => {
    if (target) map.flyTo([target.lat, target.lon], Math.max(map.getZoom(), target.zoom || 11), { duration: 0.6 })
  }, [target, map])
  return null
}

export default function MapView({ alerts = [], claims = [], selectedId, onSelect, target, layers, center = [21.5, 79], zoom = 5 }) {
  return (
    <MapContainer center={center} zoom={zoom} zoomControl={false} className="h-full w-full">
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
        className="map-tiles-mono"
      />
      <FlyTo target={target} />
      {layers.alerts &&
        alerts.filter((a) => a.polygon_geojson).map((a) => (
          <GeoJSON key={a.evidence_id} data={a.polygon_geojson}
            style={{ color: '#525252', weight: 1, dashArray: '4 3', fillColor: '#525252', fillOpacity: 0.06 }}>
            <Tooltip sticky>{`${a.source_name} · ${a.event_type} · until ${a.valid_until ? new Date(a.valid_until).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}`}</Tooltip>
          </GeoJSON>
        ))}
      {layers.alerts &&
        alerts.filter((a) => !a.polygon_geojson && a.latitude != null).map((a) => (
          <CircleMarker key={a.evidence_id} center={[a.latitude, a.longitude]} radius={4}
            pathOptions={{ color: '#525252', weight: 1, fillColor: '#fff', fillOpacity: 1 }}>
            <Tooltip>{`${a.source_name} · ${a.event_type} (${a.severity || ''})`}</Tooltip>
          </CircleMarker>
        ))}
      {layers.claims &&
        claims.filter((c) => c.latitude != null).map((c) => (
          <CircleMarker key={c.claim_id} center={[c.latitude, c.longitude]} radius={c.claim_id === selectedId ? 8 : 6}
            eventHandlers={{ click: () => onSelect?.(c.claim_id) }}
            pathOptions={{ color: c.claim_id === selectedId ? '#171717' : '#fff', weight: 2, fillColor: STATUS[c.status]?.hex || '#A3A3A3', fillOpacity: 1 }}>
            <Tooltip>{c.claim_text.slice(0, 70)}</Tooltip>
          </CircleMarker>
        ))}
    </MapContainer>
  )
}
