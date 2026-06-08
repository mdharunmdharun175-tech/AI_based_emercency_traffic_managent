import { useState, useEffect } from 'react'

const SEED = [
  { type: 'emergency', time: '11:33:01', msg: 'Ambulance KA-05-MK-4822 detected on L3' },
  { type: 'success',   time: '11:32:55', msg: 'Green corridor activated — Lane 03' },
  { type: 'info',      time: '11:32:40', msg: 'ANPR verified: plate confidence 98%' },
  { type: 'info',      time: '11:32:20', msg: 'Siren audio match: 94% probability' },
  { type: 'emergency', time: '11:31:55', msg: 'High congestion — Junction A' },
  { type: 'success',   time: '11:31:30', msg: 'Corridor cleared in 18s' },
]

const typeStyle = {
  emergency: { borderColor: '#ff4444', color: '#ff6644' },
  success:   { borderColor: '#00ff88', color: '#00dd77' },
  info:      { borderColor: '#00e5ff', color: '#4ab8d8' },
  warning:   { borderColor: '#ffaa00', color: '#ffcc44' },
}

export default function AlertFeed({ maxHeight = 150 }) {
  const [alerts, setAlerts] = useState(SEED)

  // Simulate incoming alerts every ~8s
  useEffect(() => {
    const POOL = [
      { type: 'info',      msg: 'Vehicle count updated: 47 in frame' },
      { type: 'success',   msg: 'Signal timing optimized for L2' },
      { type: 'emergency', msg: 'Accident detected — Zone B, alerting hospital' },
      { type: 'info',      msg: 'GPS sync: ambulance at 12.97°N 77.59°E' },
      { type: 'warning',   msg: 'Queue length > 200m on L1' },
    ]
    const t = setInterval(() => {
      const a = POOL[Math.floor(Math.random() * POOL.length)]
      const now = new Date().toLocaleTimeString('en-IN', { hour12: false })
      setAlerts(prev => [{ ...a, time: now }, ...prev].slice(0, 30))
    }, 8000)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 14 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 10 }}>
        System Alerts
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight, overflowY: 'auto' }}>
        {alerts.map((a, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 11, padding: '6px 10px', background: '#050a0f', borderRadius: 6, borderLeft: `2px solid ${typeStyle[a.type]?.borderColor || '#3a5a7a'}` }}>
            <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#3a5a7a', flexShrink: 0 }}>{a.time}</span>
            <span style={{ color: typeStyle[a.type]?.color || '#6a9abf', lineHeight: 1.3 }}>{a.msg}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
