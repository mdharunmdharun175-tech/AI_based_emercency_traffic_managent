import { useState } from 'react'

export default function SimulationControls({ onRefresh }) {
  const [selectedLane, setSelectedLane] = useState('Lane B')
  const [distance, setDistance] = useState(150)
  const [confidence, setConfidence] = useState(0.88)
  const [plate, setPlate] = useState('KA-05-EM-108')
  const [roofLights, setRoofLights] = useState(true)
  const [textDetected, setTextDetected] = useState(true)
  const [symbolDetected, setSymbolDetected] = useState(true)
  const [threshold, setThreshold] = useState(0.80)
  const [statusMsg, setStatusMsg] = useState('')
  const [loading, setLoading] = useState(false)

  const flash = (msg) => {
    setStatusMsg(msg)
    setTimeout(() => setStatusMsg(''), 4000)
  }

  const handleSpawn = async () => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/sim/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lane_id: selectedLane,
          distance: parseFloat(distance),
          confidence: parseFloat(confidence),
          plate: plate,
          roof_lights: roofLights,
          text_detected: textDetected,
          symbol_detected: symbolDetected,
          symbol_name: 'Red Cross',
          shape_verified: true,
        }),
      })
      const data = await res.json()
      if (res.ok) {
        flash(`🚨 Multi-Feature Ambulance Spawned on ${selectedLane} at ${distance}m (Score: ${Math.round(confidence * 100)}%)!`)
        if (onRefresh) onRefresh()
      } else {
        flash(`Error: ${data.detail || 'Spawn failed'}`)
      }
    } catch {
      flash('Backend offline — simulating trigger locally')
    } finally {
      setLoading(false)
    }
  }

  const handleConfig = async (newThresh) => {
    setThreshold(newThresh)
    try {
      await fetch('http://localhost:8000/api/signals/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confidence_threshold: parseFloat(newThresh) }),
      })
      flash(`⚙️ Combined Confirmation Threshold set to ${Math.round(newThresh * 100)}%`)
    } catch {
      /* offline */
    }
  }

  return (
    <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 14 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#00e5ff', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>🎮 Interactive Multi-Feature Ambulance Spawner & Controls</span>
        <span style={{ fontSize: 9, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>CONFIRMATION THRESHOLD: {Math.round(threshold * 100)}%</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 10 }}>
        {/* Lane Selector */}
        <div>
          <label style={{ fontSize: 9, color: '#4a6a8a', display: 'block', marginBottom: 4 }}>TARGET LANE</label>
          <select
            value={selectedLane}
            onChange={(e) => setSelectedLane(e.target.value)}
            style={{ width: '100%', background: '#050a0f', border: '1px solid #1a3a5c', borderRadius: 6, color: '#00e5ff', padding: '6px 8px', fontSize: 11, fontWeight: 700 }}
          >
            <option value="Lane A">Lane A (North)</option>
            <option value="Lane B">Lane B (East)</option>
            <option value="Lane C">Lane C (South)</option>
            <option value="Lane D">Lane D (West)</option>
          </select>
        </div>

        {/* Distance Input */}
        <div>
          <label style={{ fontSize: 9, color: '#4a6a8a', display: 'block', marginBottom: 4 }}>DISTANCE (METERS)</label>
          <input
            type="number"
            min="20"
            max="250"
            value={distance}
            onChange={(e) => setDistance(e.target.value)}
            style={{ width: '100%', background: '#050a0f', border: '1px solid #1a3a5c', borderRadius: 6, color: '#ffaa00', padding: '6px 8px', fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}
          />
        </div>

        {/* Combined Confidence Score */}
        <div>
          <label style={{ fontSize: 9, color: '#4a6a8a', display: 'block', marginBottom: 4 }}>COMBINED CONF ({Math.round(confidence * 100)}%)</label>
          <input
            type="range"
            min="0.50"
            max="0.99"
            step="0.02"
            value={confidence}
            onChange={(e) => setConfidence(e.target.value)}
            style={{ width: '100%', accentColor: '#00e5ff' }}
          />
        </div>

        {/* Plate */}
        <div>
          <label style={{ fontSize: 9, color: '#4a6a8a', display: 'block', marginBottom: 4 }}>ANPR LICENSE PLATE</label>
          <input
            type="text"
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
            style={{ width: '100%', background: '#050a0f', border: '1px solid #1a3a5c', borderRadius: 6, color: '#00ff88', padding: '6px 8px', fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}
          />
        </div>
      </div>

      {/* Multi-Feature Feature Toggles */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 10, background: '#050a0f', padding: '6px 12px', borderRadius: 6, border: '1px solid #0d2035' }}>
        <span style={{ fontSize: 9, fontWeight: 700, color: '#6a9abf', letterSpacing: 1 }}>VISUAL FEATURES:</span>
        <label style={{ fontSize: 9, color: '#a8c8e8', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
          <input type="checkbox" checked={roofLights} onChange={(e) => setRoofLights(e.target.checked)} style={{ accentColor: '#ff4444' }} />
          🔴🔵 Roof Lights (20%)
        </label>
        <label style={{ fontSize: 9, color: '#a8c8e8', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
          <input type="checkbox" checked={textDetected} onChange={(e) => setTextDetected(e.target.checked)} style={{ accentColor: '#00e5ff' }} />
          🔤 "AMBULANCE" Text (15%)
        </label>
        <label style={{ fontSize: 9, color: '#a8c8e8', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
          <input type="checkbox" checked={symbolDetected} onChange={(e) => setSymbolDetected(e.target.checked)} style={{ accentColor: '#ffaa00' }} />
          ✚ Red Cross / Star (10%)
        </label>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        {/* Spawn Button */}
        <button
          onClick={handleSpawn}
          disabled={loading}
          style={{
            flex: 1,
            padding: '8px 14px',
            background: 'linear-gradient(90deg, #ff0055, #ff4444)',
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            fontFamily: 'Rajdhani, sans-serif',
            fontWeight: 700,
            fontSize: 12,
            letterSpacing: 1.5,
            cursor: 'pointer',
            boxShadow: '0 0 10px #ff005544',
          }}
        >
          🚨 SPAWN AMBULANCE ON {selectedLane.toUpperCase()} ({distance}m)
        </button>

        {/* Threshold Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#050a0f', border: '1px solid #0d2035', padding: '4px 10px', borderRadius: 6 }}>
          <span style={{ fontSize: 9, color: '#3a5a7a' }}>CONFIRM THRESHOLD:</span>
          <span style={{ fontSize: 10, fontWeight: 700, color: '#00e5ff', width: 32, fontFamily: 'Share Tech Mono, monospace' }}>{Math.round(threshold * 100)}%</span>
          <input
            type="range"
            min="0.50"
            max="0.95"
            step="0.05"
            value={threshold}
            onChange={(e) => handleConfig(e.target.value)}
            style={{ width: 60, accentColor: '#00e5ff' }}
          />
        </div>
      </div>

      {statusMsg && (
        <div style={{ marginTop: 8, fontSize: 11, color: '#00e5ff', fontFamily: 'Share Tech Mono, monospace' }}>
          {statusMsg}
        </div>
      )}
    </div>
  )
}
