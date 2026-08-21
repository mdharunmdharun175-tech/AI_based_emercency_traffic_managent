import { useState, useEffect } from 'react'
import StatCard from '../components/StatCard'
import SignalPanel from '../components/SignalPanel'
import PriorityQueueWidget from '../components/PriorityQueueWidget'
import SimulationControls from '../components/SimulationControls'

const LANES = [
  { id: 'Lane A', label: 'LANE A (NORTH)', apiId: 'Lane A' },
  { id: 'Lane B', label: 'LANE B (EAST)',  apiId: 'Lane B' },
  { id: 'Lane C', label: 'LANE C (SOUTH)', apiId: 'Lane C' },
  { id: 'Lane D', label: 'LANE D (WEST)',  apiId: 'Lane D' },
]

function LaneCameraFeed({ lane, signalInfo }) {
  const [imgError, setImgError] = useState(false)
  const isGreen = signalInfo?.color === 'GREEN'
  const countdown = signalInfo?.countdown ?? 30
  const isEmergency = signalInfo?.is_emergency ?? false

  return (
    <div style={{
      background: '#070d14',
      border: `1px solid ${isEmergency ? '#ff4444' : isGreen ? '#00ff8844' : '#0d2035'}`,
      borderRadius: 10,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      boxShadow: isEmergency ? '0 0 12px #ff000030' : isGreen ? '0 0 10px #00ff8815' : 'none'
    }}>
      {/* Feed Header */}
      <div style={{ padding: '6px 10px', background: '#050a0f', borderBottom: '1px solid #0d2035', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#7abcdc', letterSpacing: 1.5 }}>
          {lane.label}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            padding: '2px 7px', borderRadius: 4, fontSize: 10, fontWeight: 700, fontFamily: 'Share Tech Mono, monospace',
            background: isGreen ? '#00ff8820' : '#ff444420', color: isGreen ? '#00ff88' : '#ff4444', border: `1px solid ${isGreen ? '#00ff8844' : '#ff444444'}`
          }}>
            {isGreen ? `GREEN (${countdown}s)` : `RED (${countdown}s)`}
          </div>
        </div>
      </div>

      {/* Live Video Feed Stream */}
      <div style={{ position: 'relative', height: 180, background: '#030810', overflow: 'hidden' }}>
        {!imgError ? (
          <img
            src={`http://localhost:8000/api/sim/feed/${encodeURIComponent(lane.apiId)}`}
            alt={lane.label}
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#3a5a7a' }}>
            <div style={{ fontSize: 12, fontFamily: 'Share Tech Mono, monospace', marginBottom: 4 }}>[ SIMULATION FEED ACTIVE ]</div>
            <div style={{ fontSize: 10 }}>Backend Stream Syncing...</div>
          </div>
        )}

        {isEmergency && (
          <div style={{ position: 'absolute', top: 6, left: 6, right: 6, background: '#ff000088', color: '#fff', padding: '3px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'Rajdhani, sans-serif', letterSpacing: 1 }}>
            <span style={{ width: 6, height: 6, background: '#fff', borderRadius: '50%' }} />
            🚨 EMERGENCY GREEN ACTIVE
          </div>
        )}
      </div>
    </div>
  )
}

export default function Dashboard({ ws }) {
  const [fsmData, setFsmData] = useState(ws || {})

  useEffect(() => {
    if (ws) setFsmData(ws)
  }, [ws])

  // Poll backend if ws not available
  useEffect(() => {
    const fetchFSM = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/signals/fsm_state')
        const data = await res.json()
        if (data) setFsmData(prev => ({ ...prev, ...data }))
      } catch { /* offline */ }
    }
    fetchFSM()
    const t = setInterval(fetchFSM, 1000)
    return () => clearInterval(t)
  }, [])

  const fsmState = fsmData?.controller_state || 'NORMAL'
  const signals = fsmData?.signals || {}
  const priorityQueue = fsmData?.priority_queue || []
  const logs = fsmData?.logs || []
  const pausedLane = fsmData?.paused_lane
  const pausedRem = fsmData?.paused_remaining
  const skipLanes = fsmData?.skip_lanes || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0 20px 16px', gap: 10, overflowY: 'auto' }}>

      {/* FSM Status Alert Banner */}
      <div style={{
        marginTop: 10,
        padding: '10px 16px',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        justify: 'space-between',
        background: fsmState === 'ALL_RED_SAFETY' ? '#ffaa0020' :
                    fsmState === 'EMERGENCY_GREEN' ? '#ff000025' :
                    fsmState === 'RESUME' ? '#00e5ff20' :
                    fsmState === 'SKIP' ? '#ffaa0015' : '#00ff8810',
        border: `1px solid ${fsmState === 'ALL_RED_SAFETY' ? '#ffaa0066' :
                            fsmState === 'EMERGENCY_GREEN' ? '#ff444466' :
                            fsmState === 'RESUME' ? '#00e5ff66' : '#00ff8844'}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: fsmState === 'ALL_RED_SAFETY' ? '#ffaa00' :
                        fsmState === 'EMERGENCY_GREEN' ? '#ff4444' : '#00ff88',
            boxShadow: `0 0 10px ${fsmState === 'EMERGENCY_GREEN' ? '#ff4444' : '#00ff88'}`
          }} />
          <div>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#a8c8e8', letterSpacing: 1.5, marginRight: 10 }}>
              FSM CONTROLLER STATE:
            </span>
            <span style={{
              fontFamily: 'Rajdhani, sans-serif', fontSize: 14, fontWeight: 700, letterSpacing: 2,
              color: fsmState === 'EMERGENCY_GREEN' ? '#ff4444' : fsmState === 'ALL_RED_SAFETY' ? '#ffaa00' : '#00ff88'
            }}>
              [{fsmState}] {
                fsmState === 'ALL_RED_SAFETY' ? '— 2s ALL-RED SAFETY DELAY IN PROGRESS' :
                fsmState === 'EMERGENCY_GREEN' ? `— EMERGENCY GREEN ACTIVE ON ${fsmData?.active_emergency_lane} (HOLDING UNTIL STOP LINE CROSSING)` :
                fsmState === 'RESUME' ? `— RESUMING INTERRUPTED ${pausedLane} (${pausedRem}s REMAINING)` :
                '— NORMAL 30s CIRCULAR ROTATION (A → B → C → D)'
              }
            </span>
          </div>
        </div>

        {skipLanes.length > 0 && (
          <div style={{ fontSize: 10, background: '#ffaa0020', border: '1px solid #ffaa0055', color: '#ffaa00', padding: '2px 8px', borderRadius: 4, fontFamily: 'Share Tech Mono, monospace' }}>
            SKIP LIST: {skipLanes.join(', ')}
          </div>
        )}
      </div>

      {/* Top Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
        <StatCard label="FSM Mode" value={fsmState} delta="ACTIVE" accent="#00e5ff" />
        <StatCard label="Priority Queue" value={`${priorityQueue.length} Vehicles`} delta="LIVE" accent="#ff4444" />
        <StatCard label="Active Green Lane" value={fsmData?.active_green_lane || 'Lane A'} delta="30s CYCLE" accent="#00ff88" />
        <StatCard label="Total Detections" value={fsmData?.total_detections || 142} delta="SQLITE LOGGED" accent="#4488ff" />
      </div>

      {/* Interactive Ambulance Spawner Bar */}
      <SimulationControls />

      {/* Main Grid: 4-Lane Junction Video Feeds (Left) + Queue/Signals/Logs (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 10, flex: 1, minHeight: 0 }}>

        {/* Left: 4 Camera Junction Video Feeds in 2x2 Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase' }}>
            4-LANE INTERSECTION CAMERA FEEDS & TRAFFIC SIGNALS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, flex: 1 }}>
            {LANES.map(lane => (
              <LaneCameraFeed
                key={lane.id}
                lane={lane}
                signalInfo={signals[lane.id]}
              />
            ))}
          </div>
        </div>

        {/* Right Side: Priority Queue + Signal Panel + Real-Time Event Logs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto' }}>
          <PriorityQueueWidget priorityQueue={priorityQueue} activeEmergencyLane={fsmData?.active_emergency_lane} />

          <SignalPanel lanes={Object.keys(signals).map(k => ({
            lane_id: k,
            name: `${k} Junction`,
            state: signals[k].color.toLowerCase(),
            priority: signals[k].is_emergency,
            countdown: signals[k].countdown,
          }))} />

          {/* System Event Logs Panel */}
          <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 12, display: 'flex', flexDirection: 'column', height: 220 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#00e5ff', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 8 }}>
              📜 Real-Time System Event Logs
            </div>
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, fontFamily: 'Share Tech Mono, monospace', fontSize: 10 }}>
              {logs.length > 0 ? (
                logs.map((log, idx) => (
                  <div key={idx} style={{ padding: '3px 6px', background: '#050a0f', borderRadius: 4, borderLeft: `2px solid ${log.log_level === 'INFO' ? '#00e5ff' : '#ff4444'}`, color: '#a8c8e8' }}>
                    <span style={{ color: '#3a5a7a', marginRight: 6 }}>
                      {new Date((log.timestamp || 0) * 1000).toLocaleTimeString()}
                    </span>
                    <span style={{ color: '#00ff88', fontWeight: 700, marginRight: 6 }}>
                      [{log.category || 'EVENT'}]
                    </span>
                    {log.message}
                  </div>
                ))
              ) : (
                <div style={{ color: '#3a5a7a', textAlign: 'center', marginTop: 20 }}>No logs recorded yet</div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}