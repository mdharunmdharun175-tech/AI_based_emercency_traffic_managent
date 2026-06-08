import { useState } from 'react'

const Section = ({ title, children }) => (
  <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 16, marginBottom: 12 }}>
    <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 14, borderBottom: '1px solid #0d2035', paddingBottom: 8 }}>
      {title}
    </div>
    {children}
  </div>
)

const Field = ({ label, value, onChange, type = 'text', note }) => (
  <div style={{ marginBottom: 14 }}>
    <label style={{ display: 'block', fontSize: 11, color: '#4a6a8a', marginBottom: 5, letterSpacing: 0.5 }}>{label}</label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        width: '100%', maxWidth: 360,
        background: '#050a0f', border: '1px solid #0d2035', borderRadius: 6,
        color: '#c8d8e8', padding: '8px 10px', fontSize: 12,
        fontFamily: type === 'number' ? 'Share Tech Mono, monospace' : 'inherit',
        outline: 'none',
      }}
    />
    {note && <div style={{ fontSize: 10, color: '#3a5a7a', marginTop: 4 }}>{note}</div>}
  </div>
)

const Toggle = ({ label, value, onChange, note }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, maxWidth: 400 }}>
    <div>
      <div style={{ fontSize: 12, color: '#c8d8e8' }}>{label}</div>
      {note && <div style={{ fontSize: 10, color: '#3a5a7a', marginTop: 2 }}>{note}</div>}
    </div>
    <div
      onClick={() => onChange(!value)}
      style={{
        width: 40, height: 22, borderRadius: 11, cursor: 'pointer', position: 'relative',
        background: value ? '#00e5ff44' : '#0d2035',
        border: `1px solid ${value ? '#00e5ff88' : '#1a3a5c'}`,
        transition: 'all 0.2s',
      }}
    >
      <div style={{
        position: 'absolute', top: 2, width: 16, height: 16, borderRadius: '50%',
        background: value ? '#00e5ff' : '#3a5a7a',
        left: value ? 20 : 2,
        transition: 'all 0.2s',
      }} />
    </div>
  </div>
)

export default function Settings() {
  const [cfg, setCfg] = useState({
    backendUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws',
    confidenceThreshold: 0.55,
    greenDuration: 30,
    arduinoPort: '/dev/ttyUSB0',
    arduinoBaud: 9600,
    cameraFps: 10,
    sirenDetection: true,
    autoCorridors: true,
    mongoUri: 'mongodb://localhost:27017/ai_traffic',
    mapsKey: '',
    logLevel: 'INFO',
    requireApiKey: false,
  })
  const [saved, setSaved] = useState(false)

  const set = (key) => (val) => setCfg(prev => ({ ...prev, [key]: val }))

  const handleSave = () => {
    // In production: POST to /api/config
    localStorage.setItem('ai_traffic_config', JSON.stringify(cfg))
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div style={{ padding: '14px 20px', height: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 680 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 14 }}>
          SYSTEM CONFIGURATION
        </div>

        <Section title="Backend Connection">
          <Field label="API Base URL"   value={cfg.backendUrl} onChange={set('backendUrl')} />
          <Field label="WebSocket URL"  value={cfg.wsUrl}       onChange={set('wsUrl')} />
          <Field label="Log Level"      value={cfg.logLevel}    onChange={set('logLevel')} note="INFO | DEBUG | WARNING | ERROR" />
          <Toggle label="Require API Key" value={cfg.requireApiKey} onChange={set('requireApiKey')} note="Adds X-API-Key header validation" />
        </Section>

        <Section title="AI Detection">
          <Field label="YOLOv8 Confidence Threshold" value={cfg.confidenceThreshold} onChange={set('confidenceThreshold')} type="number" note="0.0–1.0 — lower = more detections, higher = fewer false positives" />
          <Field label="Camera FPS (stream rate)"    value={cfg.cameraFps}           onChange={set('cameraFps')} type="number" />
          <Toggle label="Siren Audio Detection"   value={cfg.sirenDetection} onChange={set('sirenDetection')} note="Uses CNN on microphone input to confirm ambulance" />
          <Toggle label="Auto Corridor Activation" value={cfg.autoCorridors}  onChange={set('autoCorridors')} note="Automatically set GREEN when ambulance detected" />
        </Section>

        <Section title="Signal Control">
          <Field label="Green Corridor Duration (s)" value={cfg.greenDuration} onChange={set('greenDuration')} type="number" note="Seconds to hold green before auto-reset" />
          <Field label="Arduino Serial Port"          value={cfg.arduinoPort}   onChange={set('arduinoPort')}  note="Linux: /dev/ttyUSB0 | Windows: COM3" />
          <Field label="Arduino Baud Rate"            value={cfg.arduinoBaud}   onChange={set('arduinoBaud')}  type="number" />
        </Section>

        <Section title="Database">
          <Field label="MongoDB URI" value={cfg.mongoUri} onChange={set('mongoUri')} note="mongodb://host:port/database" />
        </Section>

        <Section title="External APIs">
          <Field label="Google Maps API Key" value={cfg.mapsKey} onChange={set('mapsKey')} type="password" note="Required for live GPS map on mobile app" />
        </Section>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={handleSave}
            style={{ padding: '11px 28px', background: '#00e5ff22', border: '1px solid #00e5ff55', borderRadius: 8, color: '#00e5ff', fontFamily: 'Rajdhani, sans-serif', fontSize: 13, fontWeight: 700, letterSpacing: 2, cursor: 'pointer' }}
          >
            SAVE CONFIGURATION
          </button>
          {saved && <span style={{ fontSize: 12, color: '#00ff88', fontFamily: 'Share Tech Mono, monospace' }}>✓ Saved</span>}
        </div>
      </div>
    </div>
  )
}
