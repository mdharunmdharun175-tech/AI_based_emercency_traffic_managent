import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const makeIcon = (color, size = 12) => L.divIcon({
  html: `<div style="width:${size}px;height:${size}px;background:${color};border:2px solid #fff;border-radius:50%;box-shadow:0 0 10px ${color}"></div>`,
  iconSize:   [size, size],
  iconAnchor: [size/2, size/2],
  className:  '',
})

const ambIcon = makeIcon('#00e5ff', 14)
const carIcon = makeIcon('#4488ff', 10)

const VEHICLES_INIT = [
  { id: 'AMB-001', type: 'Ambulance', plate: 'KA-05-MK-4822', lat: 12.9716, lng: 77.5946, speed: 62, status: 'en-route' },
  { id: 'AMB-002', type: 'Ambulance', plate: 'KA-01-AB-1234', lat: 12.9831, lng: 77.6012, speed: 45, status: 'idle'     },
  { id: 'CAR-047', type: 'Car',       plate: 'KA-09-XY-7890', lat: 12.9650, lng: 77.5880, speed: 30, status: 'moving'   },
]

function AutoPan({ lat, lng }) {
  const map = useMap()
  useEffect(() => { map.panTo([lat, lng], { animate: true, duration: 1.2 }) }, [lat, lng])
  return null
}

export default function GPSTracking() {
  const [selected,  setSelected]  = useState('AMB-001')
  const [positions, setPositions] = useState(VEHICLES_INIT)

  useEffect(() => {
    const t = setInterval(() => {
      setPositions(prev => prev.map(v => ({
        ...v,
        lat:   v.lat + (Math.random() - 0.5) * 0.0004,
        lng:   v.lng + (Math.random() - 0.5) * 0.0004,
        speed: Math.max(5, Math.round(v.speed + (Math.random()-0.5)*5)),
      })))
    }, 2000)
    return () => clearInterval(t)
  }, [])

  const sel      = positions.find(v => v.id === selected)
  const sigColor = { 'en-route': '#00e5ff', idle: '#4488ff', moving: '#00ff88' }

  return (
    <div style={{ padding: '14px 20px', height: '100%', display: 'flex', gap: 12, overflow: 'hidden' }}>

      {/* Vehicle list */}
      <div style={{ width: 260, display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 4 }}>TRACKED VEHICLES</div>
        {positions.map(v => (
          <div
            key={v.id}
            onClick={() => setSelected(v.id)}
            style={{
              padding: '12px 14px', cursor: 'pointer', borderRadius: 10,
              background: selected === v.id ? '#0d2a40' : '#070d14',
              border:     `1px solid ${selected === v.id ? '#00e5ff44' : '#0d2035'}`,
              boxShadow:  selected === v.id ? '0 0 12px #00e5ff15' : 'none',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 12, color: '#00e5ff', fontWeight: 700 }}>{v.id}</span>
              <span style={{ fontSize: 10, color: sigColor[v.status], fontWeight: 700 }}>{v.status.toUpperCase()}</span>
            </div>
            <div style={{ fontSize: 11, color: '#6a9abf', marginBottom: 4 }}>
              {v.type === 'Ambulance' ? '🚑' : '🚗'} {v.type} — {v.plate}
            </div>
            <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#3a5a7a' }}>
              {v.lat.toFixed(4)}°N {v.lng.toFixed(4)}°E
            </div>
            <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#3a5a7a', marginTop: 2 }}>
              Speed: {v.speed} km/h
            </div>
          </div>
        ))}

        {/* Legend */}
        <div style={{ marginTop: 8, padding: '10px 12px', background: '#070d14', border: '1px solid #0d2035', borderRadius: 8 }}>
          <div style={{ fontSize: 9, color: '#3a5a7a', letterSpacing: 1.5, marginBottom: 8 }}>LEGEND</div>
          {[{ color: '#00e5ff', label: 'Ambulance' }, { color: '#4488ff', label: 'Vehicle' }].map(l => (
            <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: l.color, boxShadow: `0 0 6px ${l.color}` }} />
              <span style={{ fontSize: 11, color: '#4a6a8a' }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Map panel */}
      <div style={{ flex: 1, background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #0d2035', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0, background: '#050a0f' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#4a6a8a', letterSpacing: 2 }}>
            🗺 LIVE MAP — BENGALURU
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff88' }} />
            <span style={{ fontSize: 10, color: '#00ff88', fontFamily: 'Share Tech Mono, monospace' }}>
              TRACKING: {selected}
            </span>
          </div>
        </div>

        {/* Leaflet real map */}
        <div style={{ flex: 1, position: 'relative' }}>
          <MapContainer
            center={[12.9716, 77.5946]}
            zoom={14}
            style={{ height: '100%', width: '100%' }}
            zoomControl
          >
            {/* Dark OpenStreetMap tiles — no API key needed */}
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            />

            {/* Auto pan to selected vehicle */}
            {sel && <AutoPan lat={sel.lat} lng={sel.lng} />}

            {/* Vehicle markers */}
            {positions.map(v => (
              <Marker
                key={v.id}
                position={[v.lat, v.lng]}
                icon={v.type === 'Ambulance' ? ambIcon : carIcon}
                eventHandlers={{ click: () => setSelected(v.id) }}
              >
                <Popup>
                  <div style={{ fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6 }}>
                    <strong style={{ color: '#00e5ff' }}>{v.id}</strong><br />
                    Type: {v.type}<br />
                    Plate: {v.plate}<br />
                    Speed: {v.speed} km/h<br />
                    Status: <span style={{ color: sigColor[v.status] }}>{v.status}</span>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>

        {/* Vehicle info bar */}
        {sel && (
          <div style={{ padding: '10px 16px', borderTop: '1px solid #0d2035', display: 'flex', gap: 24, flexShrink: 0, background: '#050a0f' }}>
            {[
              { label: 'VEHICLE', value: sel.id,                    color: '#00e5ff' },
              { label: 'PLATE',   value: sel.plate,                 color: '#ffaa00' },
              { label: 'SPEED',   value: `${sel.speed} km/h`,       color: '#00ff88' },
              { label: 'LAT',     value: sel.lat.toFixed(5),        color: '#c8d8e8' },
              { label: 'LNG',     value: sel.lng.toFixed(5),        color: '#c8d8e8' },
              { label: 'STATUS',  value: sel.status.toUpperCase(),  color: sigColor[sel.status] },
            ].map(f => (
              <div key={f.label}>
                <div style={{ fontSize: 9, color: '#3a5a7a', letterSpacing: 1, marginBottom: 3 }}>{f.label}</div>
                <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: f.color, fontWeight: 700 }}>{f.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}