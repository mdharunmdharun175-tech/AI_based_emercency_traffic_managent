import { useState, useEffect } from 'react'
import { overrideSignal, resetSignals } from '../utils/api'

const DEFAULT_LANES = [
  { lane_id: 'Lane A', name: 'Lane A Junction', state: 'green', countdown: 30 },
  { lane_id: 'Lane B', name: 'Lane B Junction', state: 'red',   countdown: 30 },
  { lane_id: 'Lane C', name: 'Lane C Junction', state: 'red',   countdown: 60 },
  { lane_id: 'Lane D', name: 'Lane D Junction', state: 'red',   countdown: 90 },
]

export default function SignalPanel({ lanes: propLanes }) {
  const [lanes, setLanes]     = useState(propLanes && propLanes.length > 0 ? propLanes : DEFAULT_LANES)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg]         = useState('')

  useEffect(() => {
    if (propLanes && propLanes.length > 0) {
      setLanes(propLanes)
    }
  }, [propLanes])

  const flash = (text) => { setMsg(text); setTimeout(() => setMsg(''), 3000) }

  const handleOverride = async (laneId, state) => {
    setLoading(true)
    try {
      await overrideSignal({ lane_id: laneId, state, duration_seconds: 30 })
      setLanes(prev => prev.map(l => l.lane_id === laneId ? { ...l, state } : l))
      flash(`${laneId} → ${state.toUpperCase()} (manual override)`)
    } catch { flash('API not reachable – simulating locally') } finally { setLoading(false) }
  }

  const handleReset = async () => {
    setLoading(true)
    try { await resetSignals() } catch { /* simulate */ } finally {
      setLanes(DEFAULT_LANES); flash('Signals reset to normal'); setLoading(false)
    }
  }

  const stateColor = { green: '#00ff88', red: '#ff4444', yellow: '#ffaa00' }

  return (
    <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 14 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>Signal Controller (FSM)</span>
        <span style={{ fontSize: 9, color: '#00e5ff', fontFamily: 'Share Tech Mono, monospace' }}>30s CIRCULAR CYCLE</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
        {lanes.map(lane => (
          <div key={lane.lane_id} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 12px', background: lane.state === 'green' ? '#00ff8808' : '#050a0f',
            border: `1px solid ${lane.state === 'green' ? '#00ff8840' : '#0d2035'}`, borderRadius: 8,
          }}>
            <div>
              <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: '#3a5a7a', marginRight: 8 }}>{lane.lane_id}</span>
              <span style={{ fontSize: 12, color: '#6a9abf' }}>{lane.name}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: stateColor[lane.state] || '#ff4444', boxShadow: `0 0 6px ${stateColor[lane.state] || '#ff4444'}` }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: stateColor[lane.state] || '#ff4444', letterSpacing: 0.5, fontFamily: 'Share Tech Mono, monospace' }}>
                {lane.state === 'green' ? `GREEN (${lane.countdown ?? 30}s)` : `RED (${lane.countdown ?? 30}s)`}
              </span>
              <button
                onClick={() => handleOverride(lane.lane_id, lane.state === 'green' ? 'red' : 'green')}
                disabled={loading}
                style={{ fontSize: 10, background: '#0d2035', border: '1px solid #1a3a5c', borderRadius: 4, color: '#4a8aaa', padding: '2px 7px', cursor: 'pointer' }}
              >
                TOGGLE
              </button>
            </div>
          </div>
        ))}
      </div>

      {msg && <div style={{ fontSize: 11, color: '#00e5ff', marginBottom: 8, fontFamily: 'Share Tech Mono, monospace' }}>{msg}</div>}

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={() => handleOverride('Lane B', 'green')}
          style={{ flex: 1, padding: 10, background: '#00e5ff18', border: '1px solid #00e5ff44', borderRadius: 8, color: '#00e5ff', fontFamily: 'Rajdhani, sans-serif', fontSize: 12, fontWeight: 700, letterSpacing: 1.5, cursor: 'pointer' }}
        >
          OVERRIDE MANUAL
        </button>
        <button
          onClick={handleReset}
          style={{ padding: '10px 14px', background: '#ff444415', border: '1px solid #ff444430', borderRadius: 8, color: '#ff6644', fontFamily: 'Rajdhani, sans-serif', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
        >
          RESET
        </button>
      </div>
    </div>
  )
}
