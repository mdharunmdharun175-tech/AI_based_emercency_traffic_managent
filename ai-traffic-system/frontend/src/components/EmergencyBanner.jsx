/**
 * EmergencyBanner — shown at the top of the dashboard
 * when an ambulance is actively detected.
 */
import { useState, useEffect } from 'react'

export default function EmergencyBanner({ detected, plate, lane }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    setVisible(detected)
  }, [detected])

  if (!visible) return null

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
      background: 'linear-gradient(90deg, #ff000022, #ff440044, #ff000022)',
      border: '1px solid #ff444466',
      borderTop: 'none',
      padding: '8px 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      backdropFilter: 'blur(4px)',
      animation: 'emergencyPulse 1.5s ease-in-out infinite',
    }}>
      <style>{`
        @keyframes emergencyPulse {
          0%,100% { background: linear-gradient(90deg,#ff000022,#ff440044,#ff000022); }
          50%      { background: linear-gradient(90deg,#ff000044,#ff440088,#ff000044); }
        }
      `}</style>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 16 }}>🚨</span>
        <span style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 14, fontWeight: 700, color: '#ff4444', letterSpacing: 2 }}>
          EMERGENCY VEHICLE DETECTED
        </span>
        {plate && (
          <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 13, color: '#ff8888', background: '#ff000020', padding: '2px 8px', borderRadius: 4, border: '1px solid #ff444440' }}>
            {plate}
          </span>
        )}
        {lane && (
          <span style={{ fontSize: 12, color: '#ff6666' }}>→ Green corridor: {lane}</span>
        )}
      </div>

      <button
        onClick={() => setVisible(false)}
        style={{ background: 'none', border: 'none', color: '#ff6666', cursor: 'pointer', fontSize: 16 }}
      >
        ✕
      </button>
    </div>
  )
}
