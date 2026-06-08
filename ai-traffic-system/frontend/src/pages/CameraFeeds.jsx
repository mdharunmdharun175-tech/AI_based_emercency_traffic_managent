import { useState, useRef, useCallback, useEffect } from 'react'

const CAMS = [
  { id: 'CAM-01', loc: 'Main Junction',  lane: 'L1', active: true  },
  { id: 'CAM-02', loc: 'Highway Entry',  lane: 'L2', active: true  },
  { id: 'CAM-03', loc: 'City Cross A',   lane: 'L3', active: false },
  { id: 'CAM-04', loc: 'Hospital Gate',  lane: 'L4', active: true  },
]

const COLORS = {
  ambulance:   '#ff4444',
  police:      '#0088ff',
  fire_engine: '#ff6600',
  car:         '#00aaff',
  truck:       '#ffaa00',
  bus:         '#aa44ff',
  motorcycle:  '#00ff88',
  auto:        '#ff88cc',
  unknown:     '#ffffff',
}

function CameraBox({ cam, signalStates, onAmbulanceDetected }) {
  const [videoSrc,     setVideoSrc]     = useState(null)
  const [videoName,    setVideoName]    = useState('')
  const [detecting,    setDetecting]    = useState(false)
  const [ambulance,    setAmbulance]    = useState(false)
  const [plate,        setPlate]        = useState(null)
  const [vehicleCount, setVehicleCount] = useState(0)
  const [procMs,       setProcMs]       = useState(0)
  const [vidDims,      setVidDims]      = useState({ w: 640, h: 360 })

  const fileRef     = useRef()
  const videoRef    = useRef()
  const captureRef  = useRef()
  const overlayRef  = useRef()
  const detectRef   = useRef()
  const animRef     = useRef()
  const vehiclesRef = useRef([])

  // ── Draw boxes ────────────────────────────────────────
  const drawFrame = useCallback(() => {
    const canvas = overlayRef.current
    const video  = videoRef.current
    if (!canvas || !video) {
      animRef.current = requestAnimationFrame(drawFrame)
      return
    }

    const W = canvas.offsetWidth
    const H = canvas.offsetHeight
    canvas.width  = W
    canvas.height = H

    const ctx    = canvas.getContext('2d')
    ctx.clearRect(0, 0, W, H)

    const list   = vehiclesRef.current
    const scaleX = W / vidDims.w
    const scaleY = H / vidDims.h

    list.forEach(v => {
      const color = COLORS[v.type] || '#00aaff'
      const bb    = v.bbox
      const x     = bb.x      * scaleX
      const y     = bb.y      * scaleY
      const bw    = bb.width  * scaleX
      const bh    = bb.height * scaleY
      const isAmb = v.is_emergency

      ctx.save()
      if (isAmb) {
        ctx.shadowBlur  = 20
        ctx.shadowColor = '#ff4444'
      }
      ctx.strokeStyle = color
      ctx.lineWidth   = isAmb ? 3.5 : 1.5
      ctx.strokeRect(x, y, bw, bh)
      ctx.restore()

      // Label
      const label = isAmb
        ? `AMBULANCE ${Math.round(v.confidence * 100)}%`
        : `${v.type.toUpperCase()} ${Math.round(v.confidence * 100)}%`
      ctx.font    = `bold ${isAmb ? 13 : 10}px monospace`
      const tw    = ctx.measureText(label).width
      ctx.fillStyle = color + 'dd'
      ctx.fillRect(x, y - 18, tw + 8, 18)
      ctx.fillStyle = isAmb ? '#ffffff' : '#000000'
      ctx.fillText(label, x + 4, y - 4)

      // Ambulance extras
      if (isAmb) {
        const br = 10
        ctx.strokeStyle = '#ff4444'
        ctx.lineWidth   = 2.5
        const corners = [
          [[x, y+br],[x, y],[x+br, y]],
          [[x+bw-br, y],[x+bw, y],[x+bw, y+br]],
          [[x, y+bh-br],[x, y+bh],[x+br, y+bh]],
          [[x+bw-br, y+bh],[x+bw, y+bh],[x+bw, y+bh-br]],
        ]
        corners.forEach(pts => {
          ctx.beginPath()
          ctx.moveTo(pts[0][0], pts[0][1])
          ctx.lineTo(pts[1][0], pts[1][1])
          ctx.lineTo(pts[2][0], pts[2][1])
          ctx.stroke()
        })

        const cx = x + bw/2, cy = y + bh/2, cs = 12
        ctx.strokeStyle = '#ff4444'
        ctx.lineWidth   = 4
        ctx.beginPath(); ctx.moveTo(cx, cy-cs); ctx.lineTo(cx, cy+cs); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(cx-cs, cy); ctx.lineTo(cx+cs, cy); ctx.stroke()

        const alpha = Math.sin(Date.now() / 400) * 0.4 + 0.6
        ctx.strokeStyle = `rgba(255,68,68,${alpha})`
        ctx.lineWidth   = 2
        ctx.beginPath()
        ctx.arc(cx, cy, Math.max(bw, bh) / 2 + 14, 0, Math.PI * 2)
        ctx.stroke()
      }
    })

    animRef.current = requestAnimationFrame(drawFrame)
  }, [vidDims])

  useEffect(() => {
    if (videoSrc) {
      animRef.current = requestAnimationFrame(drawFrame)
    }
    return () => cancelAnimationFrame(animRef.current)
  }, [videoSrc, drawFrame])

  // ── File picker ───────────────────────────────────────
  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setVideoName(file.name)
    setVideoSrc(URL.createObjectURL(file))
    vehiclesRef.current = []
    setAmbulance(false)
    setPlate(null)
  }

  // ── Detection loop ────────────────────────────────────
  const startDetection = () => {
    if (detectRef.current) clearInterval(detectRef.current)
    setDetecting(true)

    detectRef.current = setInterval(async () => {
      const video  = videoRef.current
      const canvas = captureRef.current
      if (!video || !canvas || video.paused || video.ended) return

      const W = video.videoWidth  || 640
      const H = video.videoHeight || 360
      canvas.width  = 640
      canvas.height = Math.round(640 * H / W)
      setVidDims({ w: canvas.width, h: canvas.height })

      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

      canvas.toBlob(async (blob) => {
        try {
          const form = new FormData()
          form.append('file', blob, 'frame.jpg')
          const res  = await fetch('http://localhost:8000/api/detect', { method: 'POST', body: form })
          if (!res.ok) return
          const data = await res.json()

          const vList  = data.vehicles || []
          const hasAmb = vList.some(v => v.is_emergency)

          vehiclesRef.current = vList
          setVehicleCount(vList.length)
          setProcMs(Math.round(data.processing_time_ms || 0))
          setAmbulance(hasAmb)

          if (hasAmb) {
            setPlate(data.ambulance_plate)
            onAmbulanceDetected(cam.lane)
          }
        } catch { /* backend offline */ }
      }, 'image/jpeg', 0.85)
    }, 350)
  }

  // ── Stop ──────────────────────────────────────────────
  const stop = () => {
    clearInterval(detectRef.current)
    cancelAnimationFrame(animRef.current)
    setDetecting(false)
    setVideoSrc(null)
    setVideoName('')
    vehiclesRef.current = []
    setAmbulance(false)
    setPlate(null)
    setVehicleCount(0)
    const c = overlayRef.current
    if (c) c.getContext('2d').clearRect(0, 0, c.width, c.height)
  }

  const mySignal = signalStates[cam.lane] || 'red'
  const sigColor = { green: '#00ff88', red: '#ff4444', yellow: '#ffaa00' }
  const sigLabel = { green: 'GREEN', red: 'RED', yellow: 'YELLOW' }

  return (
    <div style={{
      background: '#070d14',
      border: `2px solid ${ambulance ? '#ff4444' : mySignal === 'green' ? '#00ff8866' : '#0d2035'}`,
      borderRadius: 12, overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
      boxShadow: ambulance ? '0 0 24px #ff444433' : mySignal === 'green' ? '0 0 16px #00ff8822' : 'none',
      transition: 'all 0.4s',
    }}>

      {/* Header */}
      <div style={{ padding: '7px 10px', borderBottom: '1px solid #0d2035', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#050a0f', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: '#6a9abf', letterSpacing: 1.5 }}>{cam.id} — {cam.loc}</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 8, color: cam.active ? '#00ff88' : '#ff4444' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} />
            {cam.active ? 'LIVE' : 'OFFLINE'}
          </span>
          <span style={{
            background: sigColor[mySignal] + '20', color: sigColor[mySignal],
            border: `1px solid ${sigColor[mySignal]}55`,
            borderRadius: 4, padding: '1px 7px', fontSize: 9, fontWeight: 700, letterSpacing: 1,
          }}>
            {cam.lane} · {sigLabel[mySignal]}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {detecting && (
            <span style={{ fontSize: 9, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>
              {vehicleCount}v · {procMs}ms
            </span>
          )}
          <input ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }} onChange={handleFile} />
          <button
            onClick={() => fileRef.current.click()}
            style={{ padding: '3px 9px', background: '#00e5ff15', border: '1px solid #00e5ff44', borderRadius: 5, color: '#00e5ff', fontSize: 9, fontWeight: 700, cursor: 'pointer', letterSpacing: 0.5 }}
          >
            📁 {videoSrc ? 'CHANGE' : 'LOAD VIDEO'}
          </button>
          {videoSrc && (
            <button onClick={stop} style={{ padding: '3px 8px', background: '#ff444415', border: '1px solid #ff444440', borderRadius: 5, color: '#ff4444', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>✕</button>
          )}
        </div>
      </div>

      {/* Video area */}
      <div style={{ flex: 1, position: 'relative', background: '#030810', minHeight: 0, overflow: 'hidden' }}>
        <canvas ref={captureRef} style={{ display: 'none' }} />

        {videoSrc ? (
          <>
            <video
              ref={videoRef}
              src={videoSrc}
              autoPlay loop muted
              onPlay={startDetection}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
            <canvas
              ref={overlayRef}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 5 }}
            />

            {/* Ambulance alert */}
            {ambulance && (
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10, background: '#ff000040', borderBottom: '1px solid #ff4444', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 8, height: 8, background: '#ff4444', borderRadius: '50%' }} />
                <span style={{ color: '#ff4444', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700, fontSize: 11, letterSpacing: 1.5 }}>
                  🚨 AMBULANCE — {cam.lane} GREEN CORRIDOR
                </span>
                {plate && <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#ffaa00', marginLeft: 'auto' }}>PLATE: {plate}</span>}
              </div>
            )}

            {/* Stats */}
            <div style={{ position: 'absolute', bottom: 6, left: 6, zIndex: 8, background: '#000000cc', border: '1px solid #ffffff15', borderRadius: 6, padding: '5px 8px' }}>
              <div style={{ fontSize: 8, color: detecting ? '#00ff88' : '#3a5a7a', letterSpacing: 1.5, marginBottom: 2 }}>
                {detecting ? '● AI ACTIVE' : '○ IDLE'}
              </div>
              <div style={{ fontSize: 10, color: '#c8d8e8' }}>
                Vehicles: <b style={{ color: '#00e5ff' }}>{vehicleCount}</b>
              </div>
              <div style={{ fontSize: 10, color: '#c8d8e8' }}>
                Ambulance: <b style={{ color: ambulance ? '#ff4444' : '#3a5a7a' }}>{ambulance ? '⚠ YES' : 'NO'}</b>
              </div>
              <div style={{ fontSize: 9, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>{procMs}ms</div>
            </div>

            {videoName && (
              <div style={{ position: 'absolute', bottom: 6, right: 6, zIndex: 8, fontSize: 8, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace', maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {videoName}
              </div>
            )}
          </>
        ) : (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, position: 'relative' }}>
            <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(#0d203512 1px,transparent 1px),linear-gradient(90deg,#0d203512 1px,transparent 1px)', backgroundSize: '20px 20px' }} />
            {cam.active ? (
              <div style={{ position: 'relative', zIndex: 2, textAlign: 'center' }}>
                <div style={{ fontSize: 24, marginBottom: 6 }}>📷</div>
                <div style={{ fontSize: 10, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace', marginBottom: 8 }}>NO VIDEO</div>
                <button
                  onClick={() => fileRef.current.click()}
                  style={{ padding: '6px 16px', background: '#00e5ff15', border: '1px solid #00e5ff44', borderRadius: 7, color: '#00e5ff', fontFamily: 'Rajdhani, sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1, cursor: 'pointer' }}
                >
                  📁 LOAD VIDEO
                </button>
              </div>
            ) : (
              <span style={{ color: '#1a3050', fontFamily: 'Share Tech Mono, monospace', fontSize: 10, position: 'relative', zIndex: 2 }}>NO SIGNAL</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main CameraFeeds page ─────────────────────────────
export default function CameraFeeds() {
  const [signalStates, setSignalStates] = useState({ L1: 'red', L2: 'red', L3: 'red', L4: 'red' })
  const [activeLane,   setActiveLane]   = useState(null)
  const resetTimer = useRef()

  const handleAmbulanceDetected = useCallback((lane) => {
    const newStates = {
      L1: lane === 'L1' ? 'green' : 'red',
      L2: lane === 'L2' ? 'green' : 'red',
      L3: lane === 'L3' ? 'green' : 'red',
      L4: lane === 'L4' ? 'green' : 'red',
    }
    setSignalStates(newStates)
    setActiveLane(lane)

    fetch(`http://localhost:8000/api/signal-control/corridor/${lane}?duration=30`, { method: 'POST' }).catch(() => {})

    clearTimeout(resetTimer.current)
    resetTimer.current = setTimeout(() => {
      setSignalStates({ L1: 'red', L2: 'red', L3: 'red', L4: 'red' })
      setActiveLane(null)
    }, 30000)
  }, [])

  const sigColor = { green: '#00ff88', red: '#ff4444', yellow: '#ffaa00' }

  return (
    <div style={{ padding: '12px 20px', height: '100%', display: 'flex', flexDirection: 'column', gap: 10, overflow: 'hidden' }}>

      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2 }}>CAMERA FEEDS — ALL JUNCTIONS</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {['L1','L2','L3','L4'].map(lane => (
            <div key={lane} style={{ display: 'flex', alignItems: 'center', gap: 5, background: '#070d14', border: `1px solid ${sigColor[signalStates[lane]]}44`, borderRadius: 6, padding: '4px 12px' }}>
              <div style={{ width: 9, height: 9, borderRadius: '50%', background: sigColor[signalStates[lane]], boxShadow: `0 0 8px ${sigColor[signalStates[lane]]}` }} />
              <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: sigColor[signalStates[lane]], fontWeight: 700 }}>
                {lane} {signalStates[lane].toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Corridor banner */}
      {activeLane && (
        <div style={{ flexShrink: 0, background: '#00ff8812', border: '1px solid #00ff8844', borderRadius: 8, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 9, height: 9, background: '#00ff88', borderRadius: '50%' }} />
          <span style={{ color: '#00ff88', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700, fontSize: 12, letterSpacing: 2 }}>
            🚑 GREEN CORRIDOR — {activeLane} IS GREEN · ALL OTHERS RED · AUTO-RESET IN 30s
          </span>
        </div>
      )}

      {/* 2x2 grid */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 10, overflow: 'hidden' }}>
        {CAMS.map(cam => (
          <CameraBox
            key={cam.id}
            cam={cam}
            signalStates={signalStates}
            onAmbulanceDetected={handleAmbulanceDetected}
          />
        ))}
      </div>
    </div>
  )
}