import { useState, useEffect } from 'react'
import NotificationCenter from './NotificationCenter'

export default function Topbar({ ws }) {
  const [notifOpen, setNotifOpen] = useState(false)
  const [time, setTime] = useState(new Date())
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t) }, [])
  const fmt = d => d.toLocaleTimeString('en-IN', { hour12: true })

  return (
    <div style={{ padding: '10px 20px', borderBottom: '1px solid #0d2035', background: '#070d14', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 12, color: '#4a6a8a', display: 'flex', alignItems: 'center', gap: 12 }}>
        <span>AI TRAFFIC CONTROL</span>
        <span style={{ color: '#0d2035' }}>|</span>
        <span style={{ color: '#00e5ff' }}>{fmt(time)}</span>
        {ws?.ambulanceDetected && (
          <span style={{ background: '#ff000025', color: '#ff4444', border: '1px solid #ff444440', borderRadius: 4, padding: '2px 8px', fontSize: 10, fontWeight: 700, letterSpacing: 1 }}>
            ⚠ AMBULANCE DETECTED
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: ws?.connected ? '#00ff88' : '#ff4444' }} />
          <span style={{ color: ws?.connected ? '#00ff88' : '#ff4444', fontFamily: 'Share Tech Mono, monospace' }}>
            {ws?.connected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
        <div style={{ width: 1, height: 16, background: '#0d2035' }} />
        <span style={{ fontSize: 11, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>
          VEHICLES: {ws?.vehicleCount ?? '--'}
        </span>
        <div style={{ width: 1, height: 16, background: '#0d2035' }} />
        <span style={{ fontSize: 11, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>
          CORRIDORS: {ws?.activeCorridors ?? '--'}
        </span>
        <div style={{ width: 1, height: 16, background: '#0d2035' }} />
        {/* Bell button */}
        <div
          onClick={() => setNotifOpen(o => !o)}
          style={{ width: 30, height: 30, background: '#0d2035', border: '1px solid #1a3a5c', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', position: 'relative' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4a6a8a" strokeWidth="2">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/>
          </svg>
          <div style={{ width: 6, height: 6, background: '#ff4444', borderRadius: '50%', position: 'absolute', top: 5, right: 5, border: '1px solid #070d14' }} />
        </div>
      </div>
      <NotificationCenter isOpen={notifOpen} onClose={() => setNotifOpen(false)} />
    </div>
  )
}
