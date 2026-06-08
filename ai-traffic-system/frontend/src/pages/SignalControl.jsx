import { useState, useEffect, useCallback } from 'react'
import AlertFeed from '../components/AlertFeed'

const JUNCTIONS = ['Junction Alpha', 'Junction Beta', 'Highway Entry', 'Hospital Gate']
const LANE_IDS  = ['L1', 'L2', 'L3', 'L4']

const DEFAULT_LANES = [
  { id: 'L1', name: 'Lane 01 Junction', status: 'red'   },
  { id: 'L2', name: 'Lane 02 Junction', status: 'red'   },
  { id: 'L3', name: 'Lane 03 Junction', status: 'green' },
  { id: 'L4', name: 'Lane 04 Junction', status: 'red'   },
]

const sigColor = { green: '#00ff88', red: '#ff4444', yellow: '#ffaa00' }
const sigLabel = { green: 'GREEN (ACTIVE)', red: 'RED (BLOCK)', yellow: 'YELLOW' }

export default function SignalControl({ ws }) {
  const [activeJunction, setActiveJunction] = useState(0)
  const [lanes,          setLanes]          = useState(DEFAULT_LANES)
  const [lastUpdate,     setLastUpdate]     = useState(new Date())
  const [msg,            setMsg]            = useState('')
  const [countdown,      setCountdown]      = useState(30)

  // ── Poll backend every second ──────────────────────────
  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const res  = await fetch('http://localhost:8000/api/signal-control')
        const data = await res.json()
        if (data?.lanes) {
          setLanes(data.lanes.map(l => ({
            id:     l.lane_id,
            name:   l.name,
            status: l.state,
          })))
          setLastUpdate(new Date())
        }
      } catch { /* backend offline — keep current state */ }
    }

    fetchSignals()
    const t = setInterval(fetchSignals, 1000)
    return () => clearInterval(t)
  }, [])

  // ── Countdown timer for active green lane ──────────────
  useEffect(() => {
    const hasGreen = lanes.some(l => l.status === 'green')
    if (!hasGreen) { setCountdown(30); return }
    const t = setInterval(() => setCountdown(c => c > 0 ? c - 1 : 30), 1000)
    return () => clearInterval(t)
  }, [lanes])

  // ── Toggle a lane ──────────────────────────────────────
  const toggleLane = useCallback(async (laneId, currentStatus) => {
    const newStatus = currentStatus === 'green' ? 'red' : 'green'
    try {
      await fetch('http://localhost:8000/api/signal-control/override', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lane_id: laneId, state: newStatus, duration_seconds: 30, reason: 'manual' }),
      })
      setLanes(prev => prev.map(l => l.id === laneId ? { ...l, status: newStatus } : l))
      setMsg(`${laneId} → ${newStatus.toUpperCase()}`)
      setTimeout(() => setMsg(''), 3000)
    } catch {
      setMsg('Backend offline — simulating locally')
      setLanes(prev => prev.map(l => l.id === laneId ? { ...l, status: newStatus } : l))
      setTimeout(() => setMsg(''), 2000)
    }
  }, [])

  // ── Activate corridor ──────────────────────────────────
  const activateCorridor = useCallback(async (laneId) => {
    try {
      await fetch(`http://localhost:8000/api/signal-control/corridor/${laneId}?duration=30`, { method: 'POST' })
    } catch { /* simulate */ }
    setLanes(prev => prev.map(l => ({ ...l, status: l.id === laneId ? 'green' : 'red' })))
    setMsg(`🚑 Green corridor: ${laneId}`)
    setTimeout(() => setMsg(''), 3000)
  }, [])

  // ── Reset all ──────────────────────────────────────────
  const resetAll = useCallback(async () => {
    try {
      await fetch('http://localhost:8000/api/signal-control/reset', { method: 'POST' })
    } catch { /* simulate */ }
    setLanes(DEFAULT_LANES)
    setMsg('Signals reset to normal')
    setTimeout(() => setMsg(''), 3000)
  }, [])

  const greenLane   = lanes.find(l => l.status === 'green')
  const activeCount = lanes.filter(l => l.status === 'green').length

  return (
    <div style={{ padding: '14px 20px', height: '100%', display: 'flex', gap: 12, overflow: 'hidden' }}>

      {/* Junction selector */}
      <div style={{ width: 200, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 4 }}>JUNCTIONS</div>
        {JUNCTIONS.map((j, i) => (
          <div
            key={j}
            onClick={() => setActiveJunction(i)}
            style={{
              padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
              background: activeJunction === i ? '#0d2a40' : '#070d14',
              border:     `1px solid ${activeJunction === i ? '#00e5ff44' : '#0d2035'}`,
              fontSize: 12,
              color:    activeJunction === i ? '#00e5ff' : '#4a6a8a',
            }}
          >
            {j}
          </div>
        ))}

        {/* Live update indicator */}
        <div style={{ marginTop: 8, padding: '10px 12px', background: '#070d14', border: '1px solid #0d2035', borderRadius: 8 }}>
          <div style={{ fontSize: 9, color: '#3a5a7a', letterSpacing: 1.5, marginBottom: 4 }}>LAST UPDATE</div>
          <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#00e5ff' }}>
            {lastUpdate.toLocaleTimeString()}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff88' }} />
            <span style={{ fontSize: 9, color: '#00ff88' }}>SYNCING EVERY 1s</span>
          </div>
        </div>
      </div>

      {/* Signal control panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2 }}>
          {JUNCTIONS[activeJunction].toUpperCase()} — SIGNAL CONTROL
        </div>

        {/* Green corridor banner */}
        {greenLane && (
          <div style={{ background: '#00ff8812', border: '1px solid #00ff8840', borderRadius: 8, padding: '8px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, background: '#00ff88', borderRadius: '50%' }} />
              <span style={{ color: '#00ff88', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700, fontSize: 12, letterSpacing: 1.5 }}>
                🚑 GREEN CORRIDOR — {greenLane.id} ACTIVE
              </span>
            </div>
            <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: '#00ff88' }}>
              AUTO-RESET: {countdown}s
            </span>
          </div>
        )}

        {/* Lane cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lanes.map(lane => (
            <div
              key={lane.id}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '14px 16px',
                background: lane.status === 'green' ? '#00ff8808' : '#070d14',
                border:     `1px solid ${lane.status === 'green' ? '#00ff8844' : '#0d2035'}`,
                borderRadius: 10,
                transition: 'all 0.3s',
                boxShadow:  lane.status === 'green' ? '0 0 12px #00ff8820' : 'none',
              }}
            >
              {/* Left: ID + name */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 13, color: '#3a5a7a', fontWeight: 700 }}>{lane.id}</span>
                <span style={{ fontSize: 13, color: '#6a9abf' }}>{lane.name}</span>
              </div>

              {/* Right: status + controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {/* Traffic light visual */}
                <div style={{ display: 'flex', gap: 5 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: lane.status === 'red' ? '#ff4444' : '#ff444433', boxShadow: lane.status === 'red' ? '0 0 8px #ff4444' : 'none', transition: 'all 0.3s' }} />
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: lane.status === 'yellow' ? '#ffaa00' : '#ffaa0033', boxShadow: lane.status === 'yellow' ? '0 0 8px #ffaa00' : 'none', transition: 'all 0.3s' }} />
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: lane.status === 'green' ? '#00ff88' : '#00ff8833', boxShadow: lane.status === 'green' ? '0 0 8px #00ff88' : 'none', transition: 'all 0.3s' }} />
                </div>

                <span style={{ fontSize: 12, fontWeight: 700, color: sigColor[lane.status], minWidth: 120, letterSpacing: 0.5 }}>
                  {sigLabel[lane.status]}
                </span>

                {/* Activate corridor button */}
                <button
                  onClick={() => activateCorridor(lane.id)}
                  style={{ padding: '5px 10px', background: '#00e5ff15', border: '1px solid #00e5ff44', borderRadius: 6, color: '#00e5ff', fontSize: 10, fontWeight: 700, cursor: 'pointer', letterSpacing: 0.5 }}
                >
                  🚑 CORRIDOR
                </button>

                {/* Toggle button */}
                <button
                  onClick={() => toggleLane(lane.id, lane.status)}
                  style={{
                    padding: '5px 12px',
                    background: lane.status === 'green' ? '#ff444415' : '#00ff8815',
                    border:     `1px solid ${lane.status === 'green' ? '#ff444444' : '#00ff8844'}`,
                    borderRadius: 6,
                    color:    lane.status === 'green' ? '#ff4444' : '#00ff88',
                    fontSize: 10, fontWeight: 700, cursor: 'pointer', letterSpacing: 0.5,
                  }}
                >
                  {lane.status === 'green' ? '→ RED' : '→ GREEN'}
                </button>
              </div>
            </div>
          ))}
        </div>

        {msg && (
          <div style={{ fontSize: 11, color: '#00e5ff', fontFamily: 'Share Tech Mono, monospace', padding: '6px 12px', background: '#00e5ff10', border: '1px solid #00e5ff33', borderRadius: 6 }}>
            {msg}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => activateCorridor('L3')}
            style={{ flex: 1, padding: 12, background: '#00e5ff18', border: '1px solid #00e5ff44', borderRadius: 8, color: '#00e5ff', fontFamily: 'Rajdhani, sans-serif', fontSize: 13, fontWeight: 700, letterSpacing: 2, cursor: 'pointer' }}
          >
            ⚡ OVERRIDE MANUAL
          </button>
          <button
            onClick={resetAll}
            style={{ padding: '12px 20px', background: '#ff444415', border: '1px solid #ff444433', borderRadius: 8, color: '#ff6644', fontFamily: 'Rajdhani, sans-serif', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
          >
            ↺ RESET ALL
          </button>
        </div>

        {/* Signal timing */}
        <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 12 }}>SIGNAL TIMING</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
            {[
              { label: 'Green Duration',  val: '30s',  accent: '#00ff88' },
              { label: 'Red Duration',    val: '45s',  accent: '#ff4444' },
              { label: 'Yellow Duration', val: '5s',   accent: '#ffaa00' },
              { label: 'Emergency Mode',  val: 'AUTO', accent: '#00e5ff' },
            ].map(t => (
              <div key={t.label} style={{ padding: '10px 12px', background: '#050a0f', border: '1px solid #0d2035', borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: '#3a5a7a', marginBottom: 4 }}>{t.label}</div>
                <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 22, fontWeight: 700, color: t.accent }}>{t.val}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Alerts */}
      <div style={{ width: 280 }}>
        <AlertFeed maxHeight={500} />
      </div>
    </div>
  )
}