import { useState, useRef, useCallback, useEffect } from 'react'
import SimulationControls from '../components/SimulationControls'

const CAMS = [
  { id: 'CAM-01', loc: 'Main Junction',  lane: 'L1', apiId: 'Lane A', active: true  },
  { id: 'CAM-02', loc: 'Highway Entry',  lane: 'L2', apiId: 'Lane B', active: true  },
  { id: 'CAM-03', loc: 'City Cross A',   lane: 'L3', apiId: 'Lane C', active: true  },
  { id: 'CAM-04', loc: 'Hospital Gate',  lane: 'L4', apiId: 'Lane D', active: true  },
]

const COLORS = {
  ambulance:   '#ff0000', // Only Ambulance is Bright Red!
  police:      '#0088ff',
  fire_engine: '#ff6600',
  car:         '#00aaff',
  truck:       '#ffaa00',
  bus:         '#aa44ff',
  motorcycle:  '#00ff88',
  auto:        '#ff88cc',
  unknown:     '#4a6b8c',
}

function CameraBox({ cam, signalInfo, onAmbulanceDetected }) {
  const [videoSrc,     setVideoSrc]     = useState(null)
  const [videoName,    setVideoName]    = useState('')
  const [detecting,    setDetecting]    = useState(true)
  const [ambulance,    setAmbulance]    = useState(false)
  const [plate,        setPlate]        = useState(null)
  const [vehicleCount, setVehicleCount] = useState(0)
  const [procMs,       setProcMs]       = useState(0)
  const [useSimFeed,   setUseSimFeed]   = useState(true)

  const fileRef        = useRef()
  const videoRef       = useRef()
  const imgRef         = useRef()
  const captureRef     = useRef()
  const overlayRef     = useRef()
  const detectRef      = useRef()
  const animRef        = useRef()
  const vehiclesRef    = useRef([])
  const captureDimsRef = useRef({ w: 640, h: 360 })

  // ── Draw bounding boxes on Canvas ───────
  const drawFrame = useCallback(() => {
    const canvas = overlayRef.current
    if (!canvas) {
      animRef.current = requestAnimationFrame(drawFrame)
      return
    }

    const W = canvas.offsetWidth || 640
    const H = canvas.offsetHeight || 360
    if (canvas.width !== W || canvas.height !== H) {
      canvas.width  = W
      canvas.height = H
    }

    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, W, H)

    const list   = vehiclesRef.current
    const capW   = captureDimsRef.current.w || 640
    const capH   = captureDimsRef.current.h || 360
    const scaleX = W / capW
    const scaleY = H / capH

    list.forEach(v => {
      const isAmb = v.is_emergency || v.type === 'ambulance'
      const bb    = v.bbox
      if (!bb) return

      const x  = bb.x      * scaleX
      const y  = bb.y      * scaleY
      const bw = bb.width  * scaleX
      const bh = bb.height * scaleY

      ctx.save()

      if (isAmb) {
        // ONLY THE AMBULANCE IS DRAWN IN BRIGHT RED WITH GLOWING RED HIGHLIGHTS & CROSSHAIRS!
        ctx.shadowBlur  = 25
        ctx.shadowColor = '#ff0000'
        ctx.strokeStyle = '#ff0000'
        ctx.lineWidth   = 3.5
        ctx.strokeRect(x, y, bw, bh)
        ctx.restore()

        // Red ambulance top label badge
        const confPct = Math.round((v.confidence || 0.95) * 100)
        const label   = `🚨 AMBULANCE ${confPct}%`
        ctx.font      = 'bold 12px monospace'
        const tw      = ctx.measureText(label).width
        
        ctx.fillStyle = '#ff0000'
        ctx.fillRect(x, y - 20 > 0 ? y - 20 : y, tw + 10, 20)
        ctx.fillStyle = '#ffffff'
        ctx.fillText(label, x + 5, y - 20 > 0 ? y - 5 : y + 14)

        // Emergency Target Crosshairs
        const cx = x + bw / 2, cy = y + bh / 2, cs = 12
        ctx.strokeStyle = '#ff0000'
        ctx.lineWidth   = 3
        ctx.beginPath(); ctx.moveTo(cx, cy - cs); ctx.lineTo(cx, cy + cs); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(cx - cs, cy); ctx.lineTo(cx + cs, cy); ctx.stroke()
      } else {
        // Regular traffic vehicles (Car, Truck, Bus, Bike) use clean standard outline
        const color     = COLORS[v.type] || '#00aaff'
        ctx.strokeStyle = color
        ctx.lineWidth   = 1.5
        ctx.strokeRect(x, y, bw, bh)
        ctx.restore()

        const confPct = Math.round((v.confidence || 0.85) * 100)
        const label   = `${(v.type || 'CAR').toUpperCase()} ${confPct}%`
        ctx.font      = '10px monospace'
        const tw      = ctx.measureText(label).width

        ctx.fillStyle = color + 'cc'
        ctx.fillRect(x, y - 16 > 0 ? y - 16 : y, tw + 6, 16)
        ctx.fillStyle = '#000000'
        ctx.fillText(label, x + 3, y - 16 > 0 ? y - 4 : y + 12)
      }
    })

    animRef.current = requestAnimationFrame(drawFrame)
  }, [])

  useEffect(() => {
    animRef.current = requestAnimationFrame(drawFrame)
    return () => cancelAnimationFrame(animRef.current)
  }, [drawFrame])

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setVideoName(file.name)
    setVideoSrc(URL.createObjectURL(file))
    setUseSimFeed(false)
    vehiclesRef.current = []
    setAmbulance(false)
    setPlate(null)
  }

  // ── Concurrent Detection Loop for ALL 4 Cameras ──
  const startDetection = useCallback(() => {
    if (detectRef.current) clearInterval(detectRef.current)

    const video = videoRef.current
    if (video && video.paused) {
      video.play().catch(() => {})
    }

    detectRef.current = setInterval(async () => {
      const vid    = videoRef.current
      const img    = imgRef.current
      const canvas = captureRef.current
      if (!canvas) return

      let sourceEl = null
      let srcW = 640, srcH = 360

      if (videoSrc && vid && !vid.paused && !vid.ended) {
        sourceEl = vid
        srcW = vid.videoWidth || 640
        srcH = vid.videoHeight || 360
      } else if (useSimFeed && img && img.complete && img.naturalWidth > 0) {
        sourceEl = img
        srcW = img.naturalWidth || 640
        srcH = img.naturalHeight || 360
      }

      if (!sourceEl) return

      canvas.width  = 640
      canvas.height = Math.max(200, Math.round(640 * srcH / srcW))
      captureDimsRef.current = { w: canvas.width, h: canvas.height }

      const ctx = canvas.getContext('2d')
      ctx.drawImage(sourceEl, 0, 0, canvas.width, canvas.height)

      canvas.toBlob(async (blob) => {
        if (!blob) return
        try {
          const form = new FormData()
          form.append('file', blob, 'frame.jpg')
          const res  = await fetch('http://localhost:8000/api/detect', { method: 'POST', body: form })
          if (!res.ok) return
          const data = await res.json()

          const vList       = data.vehicles || []
          const trackedAmbs = data.tracked_ambulances || []

          let combinedList = [...vList]
          trackedAmbs.forEach(amb => {
            if (!combinedList.some(v => v.id === amb.tracking_id)) {
              combinedList.push({
                id: amb.tracking_id,
                type: 'ambulance',
                confidence: amb.combined_score || amb.confidence,
                bbox: amb.bbox,
                is_emergency: true,
              })
            }
          })

          const hasAmb = trackedAmbs.some(a => a.verified || (a.combined_score || 0) >= 0.65) || vList.some(v => v.is_emergency)

          vehiclesRef.current = combinedList
          setVehicleCount(combinedList.length)
          setProcMs(Math.round(data.processing_time_ms || 0))
          setAmbulance(hasAmb)

          if (hasAmb) {
            const plateStr = data.ambulance_plate || (trackedAmbs[0] && trackedAmbs[0].plate) || 'KA-05-EM-108'
            setPlate(plateStr)
            onAmbulanceDetected(cam.apiId)
          }
        } catch { /* backend offline */ }
      }, 'image/jpeg', 0.85)
    }, 350)
  }, [videoSrc, useSimFeed, cam.apiId, onAmbulanceDetected])

  useEffect(() => {
    startDetection()
    return () => clearInterval(detectRef.current)
  }, [startDetection])

  const stopCustomVideo = () => {
    clearInterval(detectRef.current)
    setVideoSrc(null)
    setVideoName('')
    setUseSimFeed(true)
    vehiclesRef.current = []
    setAmbulance(false)
    setPlate(null)
  }

  const mySignal = signalInfo?.color || 'RED'
  const countdown = signalInfo?.countdown ?? 30
  const isEmergency = signalInfo?.is_emergency ?? false
  const sigColor = { GREEN: '#00ff88', RED: '#ff4444', YELLOW: '#ffaa00' }

  return (
    <div style={{
      background: '#070d14',
      border: `2px solid ${isEmergency || ambulance ? '#ff0000' : mySignal === 'GREEN' ? '#00ff8866' : '#0d2035'}`,
      borderRadius: 12, overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
      boxShadow: isEmergency || ambulance ? '0 0 28px #ff000055' : mySignal === 'GREEN' ? '0 0 16px #00ff8822' : 'none',
      transition: 'all 0.4s',
    }}>

      {/* Header */}
      <div style={{ padding: '7px 10px', borderBottom: '1px solid #0d2035', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#050a0f', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: '#6a9abf', letterSpacing: 1.5 }}>{cam.id} — {cam.loc}</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 8, color: '#00ff88' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00ff88', display: 'inline-block' }} />
            LIVE AI
          </span>
          <span style={{
            background: (sigColor[mySignal] || '#ff4444') + '20',
            color: sigColor[mySignal] || '#ff4444',
            border: `1px solid ${(sigColor[mySignal] || '#ff4444')}55`,
            borderRadius: 4, padding: '1px 7px', fontSize: 9, fontWeight: 700, letterSpacing: 1,
            fontFamily: 'Share Tech Mono, monospace'
          }}>
            {cam.lane} - {mySignal} ({countdown}s)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }} onChange={handleFile} />
          <button
            onClick={() => fileRef.current.click()}
            style={{ padding: '3px 9px', background: '#00e5ff15', border: '1px solid #00e5ff44', borderRadius: 5, color: '#00e5ff', fontSize: 9, fontWeight: 700, cursor: 'pointer', letterSpacing: 0.5 }}
          >
            📁 {videoSrc ? 'CHANGE VIDEO' : 'LOAD VIDEO'}
          </button>
          {videoSrc && (
            <button onClick={stopCustomVideo} style={{ padding: '3px 8px', background: '#ff444415', border: '1px solid #ff444440', borderRadius: 5, color: '#ff4444', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>✕ STREAM</button>
          )}
        </div>
      </div>

      {/* Video / Stream Area with Canvas Bounding Box Overlay */}
      <div style={{ flex: 1, position: 'relative', background: '#030810', minHeight: 0, overflow: 'hidden' }}>
        <canvas ref={captureRef} style={{ display: 'none' }} />

        {useSimFeed && !videoSrc ? (
          <>
            <img
              ref={imgRef}
              src={`http://localhost:8000/api/sim/feed/${encodeURIComponent(cam.apiId)}`}
              alt={cam.loc}
              crossOrigin="anonymous"
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
            <canvas
              ref={overlayRef}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 5 }}
            />
          </>
        ) : videoSrc ? (
          <>
            <video
              ref={videoRef}
              src={videoSrc}
              autoPlay loop muted playsInline
              onLoadedData={startDetection}
              onPlay={startDetection}
              onCanPlay={startDetection}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
            <canvas
              ref={overlayRef}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 5 }}
            />
          </>
        ) : null}

        {/* Emergency Alert Banner */}
        {(isEmergency || ambulance) && (
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10, background: '#ff0000aa', borderBottom: '2px solid #ff0000', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, background: '#ffffff', borderRadius: '50%' }} />
            <span style={{ color: '#ffffff', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700, fontSize: 11, letterSpacing: 1.5 }}>
              🚨 AMBULANCE DETECTED — {cam.lane} EMERGENCY GREEN CORRIDOR
            </span>
            {plate && <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#ffff00', marginLeft: 'auto', fontWeight: 700 }}>PLATE: {plate}</span>}
          </div>
        )}

        {/* Live HUD overlay */}
        <div style={{ position: 'absolute', bottom: 6, left: 6, zIndex: 8, background: '#000000cc', border: '1px solid #00e5ff33', borderRadius: 6, padding: '5px 8px' }}>
          <div style={{ fontSize: 8, color: '#00ff88', letterSpacing: 1.5, marginBottom: 2 }}>
            ● AI ACTIVE
          </div>
          <div style={{ fontSize: 10, color: '#c8d8e8' }}>
            Vehicles: <b style={{ color: '#00e5ff' }}>{vehicleCount}</b>
          </div>
          <div style={{ fontSize: 10, color: '#c8d8e8' }}>
            Ambulance: <b style={{ color: isEmergency || ambulance ? '#ff0000' : '#3a5a7a' }}>{isEmergency || ambulance ? '⚠ YES (RED BOX)' : 'NO'}</b>
          </div>
        </div>

        {videoName && (
          <div style={{ position: 'absolute', bottom: 6, right: 6, zIndex: 8, fontSize: 8, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace', maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {videoName}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main CameraFeeds Page ─────────────────────────────
export default function CameraFeeds() {
  const [fsmData, setFsmData] = useState({})

  // Poll FSM state every second
  useEffect(() => {
    const fetchFSM = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/signals/fsm_state')
        const data = await res.json()
        if (data) setFsmData(data)
      } catch { /* backend offline */ }
    }

    fetchFSM()
    const t = setInterval(fetchFSM, 1000)
    return () => clearInterval(t)
  }, [])

  const handleAmbulanceDetected = useCallback((laneApiId) => {
    fetch('http://localhost:8000/api/sim/spawn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lane_id: laneApiId, distance: 120, confidence: 0.88, plate: 'KA-05-EM-108' }),
    }).catch(() => {})
  }, [])

  const fsmState = fsmData?.controller_state || 'NORMAL'
  const signals = fsmData?.signals || {}
  const activeEmgLane = fsmData?.active_emergency_lane
  const sigColor = { GREEN: '#00ff88', RED: '#ff4444', YELLOW: '#ffaa00' }

  return (
    <div style={{ padding: '12px 20px', height: '100%', display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto' }}>

      {/* Top Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2 }}>
          CAMERA FEEDS — ALL JUNCTIONS (4-LANE INTERSECTION)
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {CAMS.map(cam => {
            const info = signals[cam.apiId] || { color: 'RED', countdown: 30 }
            const col = sigColor[info.color] || '#ff4444'
            return (
              <div key={cam.id} style={{ display: 'flex', alignItems: 'center', gap: 5, background: '#070d14', border: `1px solid ${col}44`, borderRadius: 6, padding: '4px 12px' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: col, boxShadow: `0 0 8px ${col}` }} />
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: col, fontWeight: 700 }}>
                  {cam.lane} {info.color} ({info.countdown}s)
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Active Corridor / FSM Banner */}
      <div style={{
        flexShrink: 0,
        background: fsmState === 'EMERGENCY_GREEN' ? '#ff000020' : fsmState === 'ALL_RED_SAFETY' ? '#ffaa0020' : '#00ff8812',
        border: `1px solid ${fsmState === 'EMERGENCY_GREEN' ? '#ff444455' : fsmState === 'ALL_RED_SAFETY' ? '#ffaa0055' : '#00ff8844'}`,
        borderRadius: 8,
        padding: '8px 16px',
        display: 'flex',
        alignItems: 'center',
        justify: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 9, height: 9, borderRadius: '50%',
            background: fsmState === 'EMERGENCY_GREEN' ? '#ff4444' : fsmState === 'ALL_RED_SAFETY' ? '#ffaa00' : '#00ff88',
            boxShadow: `0 0 10px ${fsmState === 'EMERGENCY_GREEN' ? '#ff4444' : '#00ff88'}`
          }} />
          <span style={{ color: fsmState === 'EMERGENCY_GREEN' ? '#ff4444' : fsmState === 'ALL_RED_SAFETY' ? '#ffaa00' : '#00ff88', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700, fontSize: 12, letterSpacing: 2 }}>
            🚨 [{fsmState}] {
              fsmState === 'EMERGENCY_GREEN' ? `GREEN CORRIDOR — ${activeEmgLane} IS GREEN · ALL OTHERS RED` :
              fsmState === 'ALL_RED_SAFETY' ? 'ALL-RED SAFETY STATE (2s DELAY) IN PROGRESS' :
              'NORMAL 30s CIRCULAR ROTATION (A → B → C → D)'
            }
          </span>
        </div>
        <span style={{ fontSize: 10, color: '#00e5ff', fontFamily: 'Share Tech Mono, monospace' }}>
          ACTIVE GREEN: {fsmData?.active_green_lane || 'Lane A'}
        </span>
      </div>

      {/* 2x2 Grid of Junction Feeds */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '220px 220px', gap: 10, flexShrink: 0 }}>
        {CAMS.map(cam => (
          <CameraBox
            key={cam.id}
            cam={cam}
            signalInfo={signals[cam.apiId]}
            onAmbulanceDetected={handleAmbulanceDetected}
          />
        ))}
      </div>

      {/* Spawner & Interactive Controls Bar */}
      <div style={{ flexShrink: 0, marginTop: 4 }}>
        <SimulationControls />
      </div>
    </div>
  )
}