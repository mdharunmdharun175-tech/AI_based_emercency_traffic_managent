import { useState, useEffect, useRef } from 'react'
import CameraCanvas from '../components/CameraCanvas'
import StatCard from '../components/StatCard'
import SignalPanel from '../components/SignalPanel'
import AlertFeed from '../components/AlertFeed'

const PRED = [
  { time: 'Now', val: 85, level: 'high' },
  { time: '+5m', val: 70, level: 'high' },
  { time: '+10m', val: 52, level: 'med' },
  { time: '+15m', val: 36, level: 'med' },
  { time: '+20m', val: 21, level: 'low' },
]
const barColor = { high: '#ff444430', med: '#ffaa0030', low: '#00ff8830' }
const txtColor = { high: '#ff4444', med: '#ffaa00', low: '#00ff88' }

// ── Single camera lane box ─────────────────────────────────
function CameraLane({ camId, label }) {
  const [videoSrc, setVideoSrc]         = useState(null)
  const [videoName, setVideoName]       = useState('')
  const [detections, setDetections]     = useState({})
  const [ambulance, setAmbulance]       = useState(false)
  const [processing, setProcessing]     = useState(false)
  const [vehicles, setVehicles]         = useState([])
  const fileRef    = useRef()
  const videoRef   = useRef()
  const canvasRef  = useRef()
  const intervalRef = useRef()

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setVideoName(file.name)
    setVideoSrc(URL.createObjectURL(file))
  }

  const startProcessing = () => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    setProcessing(true)
    intervalRef.current = setInterval(async () => {
      const video  = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || video.paused || video.ended) return
      const ctx = canvas.getContext('2d')
      canvas.width  = 640
      canvas.height = 360
      ctx.drawImage(video, 0, 0, 640, 360)
      canvas.toBlob(async (blob) => {
        try {
          const form = new FormData()
          form.append('file', blob, 'frame.jpg')
          const res  = await fetch('http://localhost:8000/api/detect/stream', { method: 'POST', body: form })
          if (res.ok) {
            const data = await res.json()
            setDetections(data)
            setAmbulance(data.ambulance_detected)
            setVehicles(data.vehicles || [])
          }
        } catch { /* backend offline */ }
      }, 'image/jpeg', 0.8)
    }, 500)
  }

  const stop = () => {
    clearInterval(intervalRef.current)
    setProcessing(false)
    setVideoSrc(null)
    setVideoName('')
    setDetections({})
    setAmbulance(false)
    setVehicles([])
  }

  return (
    <div style={{ flex: 1, background: '#070d14', border: `1px solid ${ambulance ? '#ff4444' : '#0d2035'}`, borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>

      {/* Header */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #0d2035', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: '#4a6a8a', letterSpacing: 2 }}>{camId} — {label}</span>
          <span style={{ background: '#ff000025', color: '#ff4444', border: '1px solid #ff444430', borderRadius: 4, padding: '1px 5px', fontSize: 9, display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 4, height: 4, background: '#ff4444', borderRadius: '50%', display: 'inline-block' }} />LIVE
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {processing && (
            <span style={{ fontSize: 9, color: '#00ff88', fontFamily: 'Share Tech Mono, monospace' }}>
              AI ● {detections.vehicle_count ?? 0} VEH
            </span>
          )}
          {/* Load video button */}
          <button
            onClick={() => fileRef.current.click()}
            style={{ padding: '3px 10px', background: '#00e5ff18', border: '1px solid #00e5ff44', borderRadius: 5, color: '#00e5ff', fontSize: 10, fontWeight: 700, cursor: 'pointer', fontFamily: 'Rajdhani, sans-serif', letterSpacing: 1 }}
          >
            📁 {videoSrc ? 'CHANGE' : 'LOAD VIDEO'}
          </button>
          {videoSrc && (
            <button
              onClick={stop}
              style={{ padding: '3px 8px', background: '#ff444415', border: '1px solid #ff444440', borderRadius: 5, color: '#ff4444', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Video area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', minHeight: 0 }}>
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        <input ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }} onChange={handleFile} />

        {videoSrc ? (
          <video
            ref={videoRef}
            src={videoSrc}
            autoPlay loop muted
            onPlay={startProcessing}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : (
          <CameraCanvas />
        )}

        {/* Ambulance alert */}
        {ambulance && (
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, background: '#ff000055', border: '1px solid #ff4444', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, background: '#ff4444', borderRadius: '50%' }} />
            <span style={{ color: '#ff4444', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700, fontSize: 12, letterSpacing: 1 }}>
              🚨 AMBULANCE — GREEN CORRIDOR ACTIVATED
            </span>
          </div>
        )}

        {/* Detection overlay */}
        {videoSrc && (
          <div style={{ position: 'absolute', bottom: 8, left: 8, background: '#000000bb', border: '1px solid #00e5ff33', borderRadius: 6, padding: '6px 10px' }}>
            <div style={{ fontSize: 9, color: '#00e5ff', letterSpacing: 1.5, marginBottom: 3 }}>
              {processing ? '● DETECTING' : '○ IDLE'}
            </div>
            <div style={{ fontSize: 11, color: '#c8d8e8' }}>
              Vehicles: <b style={{ color: '#00e5ff' }}>{detections.vehicle_count ?? 0}</b>
            </div>
            <div style={{ fontSize: 11, color: '#c8d8e8' }}>
              Ambulance: <b style={{ color: ambulance ? '#ff4444' : '#3a5a7a' }}>{ambulance ? 'YES ⚠' : 'NO'}</b>
            </div>
            <div style={{ fontSize: 10, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>
              {detections.processing_time_ms ?? 0}ms
            </div>
          </div>
        )}

        {/* Vehicle type tags */}
        {vehicles.length > 0 && videoSrc && (
          <div style={{ position: 'absolute', top: ambulance ? 36 : 8, right: 8, display: 'flex', flexDirection: 'column', gap: 3, maxHeight: '60%', overflow: 'hidden' }}>
            {vehicles.slice(0, 6).map((v, i) => (
              <div key={i} style={{
                background: v.is_emergency ? '#ff000044' : '#00000066',
                border: `1px solid ${v.is_emergency ? '#ff4444' : '#00e5ff33'}`,
                borderRadius: 4, padding: '2px 7px',
                fontSize: 10, fontWeight: 700,
                color: v.is_emergency ? '#ff4444' : '#7abcdc',
                fontFamily: 'Share Tech Mono, monospace',
              }}>
                {v.type} {(v.confidence * 100).toFixed(0)}%
              </div>
            ))}
            {vehicles.length > 6 && (
              <div style={{ fontSize: 9, color: '#3a5a7a', textAlign: 'right' }}>+{vehicles.length - 6} more</div>
            )}
          </div>
        )}

        {/* Video filename */}
        {videoName && (
          <div style={{ position: 'absolute', bottom: 8, right: 8, fontSize: 9, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {videoName}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Dashboard ──────────────────────────────────────────────
export default function Dashboard({ ws }) {
  const [passes, setPasses] = useState(142)
  useEffect(() => {
    const t = setInterval(() => setPasses(p => p + (Math.random() > 0.85 ? 1 : 0)), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0 20px 16px', gap: 12, overflow: 'hidden' }}>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, paddingTop: 14 }}>
        <StatCard label="Active Corridors" value={ws?.activeCorridors ?? 3} delta="+12%" accent="#00e5ff"
          icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00e5ff" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>}
        />
        <StatCard label="Congestion Level" value="High" delta="+5%" accent="#ff6644"
          icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff6644" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>}
        />
        <StatCard label="Successful Pass" value={passes} delta="+8%" accent="#00ff88"
          icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00ff88" strokeWidth="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>}
        />
        <StatCard label="Signal Uptime" value="99.9%" delta="+0.1%" accent="#4488ff"
          icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4488ff" strokeWidth="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>}
        />
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 310px', gap: 12, overflow: 'hidden' }}>

        {/* Left: TWO camera lanes stacked */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>

          {/* Camera lanes — 2 boxes */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, overflow: 'hidden' }}>
            <CameraLane camId="CAM-01" label="MAIN JUNCTION" />
            <CameraLane camId="CAM-02" label="HIGHWAY ENTRY" />
          </div>

          {/* Mini stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, flexShrink: 0 }}>
            {[
              { label: 'Vehicles Detected', value: ws?.vehicleCount || 47, pct: 58 },
              { label: 'Avg Speed (km/h)',   value: 24, pct: 40 },
              { label: 'Queue Length (m)',   value: 180, pct: 36 },
            ].map(s => (
              <div key={s.label} style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 10, padding: '10px 12px' }}>
                <div style={{ fontSize: 10, color: '#3a5a7a', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 20, fontWeight: 700, color: '#7abcdc' }}>{s.value}</div>
                <div style={{ height: 3, background: '#0d2035', borderRadius: 2, marginTop: 6 }}>
                  <div style={{ height: '100%', width: `${s.pct}%`, borderRadius: 2, background: 'linear-gradient(90deg,#00e5ff,#0088ff)' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto' }}>
          <SignalPanel />

          {/* Flow predictor */}
          <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 10 }}>Flow Predictor</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {PRED.map(p => (
                <div key={p.time} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#3a5a7a', width: 34 }}>{p.time}</div>
                  <div style={{ flex: 1, height: 18, background: '#050a0f', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${p.val}%`, background: barColor[p.level], display: 'flex', alignItems: 'center', paddingLeft: 6, fontSize: 9, fontWeight: 700, color: txtColor[p.level] }}>
                      {p.val}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* GPS */}
          <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 10 }}>GPS Tracking</div>
            <div style={{ height: 110, background: '#030810', borderRadius: 8, border: '1px solid #0d2035', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(#0d203520 1px,transparent 1px),linear-gradient(90deg,#0d203520 1px,transparent 1px)', backgroundSize: '20px 20px' }} />
              <div style={{ position: 'absolute', width: '60%', height: 1, background: 'linear-gradient(90deg,#00e5ff,transparent)', top: '50%', left: '20%' }} />
              <div style={{ position: 'absolute', left: '55%', top: '45%', width: 10, height: 10, background: '#ff4444', borderRadius: '50%', border: '2px solid #ff444480' }} />
              <div style={{ position: 'absolute', left: '40%', top: '50%', width: 10, height: 10, background: '#00e5ff', borderRadius: '50%', border: '2px solid #00e5ff80' }} />
              <div style={{ position: 'absolute', bottom: 4, right: 6, fontSize: 9, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>AMB ● 12.97°N 77.59°E</div>
            </div>
          </div>

          <AlertFeed maxHeight={130} />
        </div>
      </div>
    </div>
  )
}