/**
 * NotificationCenter — slide-out panel showing all system alerts
 * Triggered by the bell icon in the Topbar.
 */
import { useState, useEffect } from 'react'
import { getRecentDetections } from '../utils/api'

const TYPE_META = {
  emergency: { bg: '#ff444415', border: '#ff444440', dot: '#ff4444', label: 'EMERGENCY' },
  success:   { bg: '#00ff8815', border: '#00ff8840', dot: '#00ff88', label: 'SUCCESS'   },
  info:      { bg: '#00e5ff10', border: '#00e5ff30', dot: '#00e5ff', label: 'INFO'      },
  warning:   { bg: '#ffaa0015', border: '#ffaa0040', dot: '#ffaa00', label: 'WARNING'   },
}

const SEED = [
  { id: 1, type: 'emergency', time: '11:33:01', title: 'Ambulance Detected',       body: 'KA-05-MK-4822 on Lane 03 — corridor activated'  },
  { id: 2, type: 'success',   time: '11:32:55', title: 'Green Corridor Active',     body: 'L3 GREEN for 30s, all others RED'              },
  { id: 3, type: 'info',      time: '11:32:40', title: 'ANPR Verified',             body: 'Plate confidence: 98%'                         },
  { id: 4, type: 'info',      time: '11:32:20', title: 'Siren Detected',            body: 'Audio classifier confidence: 94%'              },
  { id: 5, type: 'warning',   time: '11:31:55', title: 'High Congestion',           body: 'Junction A — queue > 200m'                     },
  { id: 6, type: 'success',   time: '11:31:30', title: 'Corridor Cleared',          body: 'Avg clear time: 18s'                           },
  { id: 7, type: 'info',      time: '11:30:10', title: 'System Health',             body: 'All 4 cameras online. Arduino connected.'      },
]

export default function NotificationCenter({ isOpen, onClose }) {
  const [items, setItems] = useState(SEED)
  const [filter, setFilter] = useState('all')

  const filtered = filter === 'all' ? items : items.filter(i => i.type === filter)

  const dismiss = (id) => setItems(prev => prev.filter(i => i.id !== id))
  const dismissAll = () => setItems([])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: '#00000060', zIndex: 40 }} />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 360,
        background: '#070d14', borderLeft: '1px solid #0d2035',
        zIndex: 50, display: 'flex', flexDirection: 'column',
        animation: 'slideIn 0.2s ease',
      }}>
        <style>{`@keyframes slideIn { from { transform: translateX(100%) } to { transform: translateX(0) } }`}</style>

        {/* Header */}
        <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid #0d2035', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 16, fontWeight: 700, color: '#c8d8e8', letterSpacing: 1 }}>Notifications</div>
            <div style={{ fontSize: 10, color: '#3a5a7a', marginTop: 2 }}>{items.length} alerts</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={dismissAll} style={{ fontSize: 10, color: '#3a5a7a', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}>
              Clear all
            </button>
            <button onClick={onClose} style={{ width: 28, height: 28, background: '#0d2035', border: 'none', borderRadius: 6, cursor: 'pointer', color: '#4a6a8a', fontSize: 16 }}>
              ×
            </button>
          </div>
        </div>

        {/* Filter tabs */}
        <div style={{ padding: '8px 16px', borderBottom: '1px solid #0d2035', display: 'flex', gap: 6 }}>
          {['all', 'emergency', 'warning', 'info', 'success'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '3px 10px', borderRadius: 5, fontSize: 10, fontWeight: 600, cursor: 'pointer', letterSpacing: 0.5,
              background: filter === f ? '#0d2a40' : 'transparent',
              color:      filter === f ? '#00e5ff' : '#3a5a7a',
              border:     filter === f ? '1px solid #00e5ff44' : '1px solid transparent',
            }}>
              {f.toUpperCase()}
            </button>
          ))}
        </div>

        {/* List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', color: '#3a5a7a', fontSize: 12, marginTop: 40 }}>No notifications</div>
          )}
          {filtered.map(item => {
            const meta = TYPE_META[item.type] || TYPE_META.info
            return (
              <div key={item.id} style={{ background: meta.bg, border: `1px solid ${meta.border}`, borderRadius: 10, padding: '10px 12px', position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ width: 7, height: 7, borderRadius: '50%', background: meta.dot, flexShrink: 0, marginTop: 4 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#c8d8e8' }}>{item.title}</span>
                      <span style={{ fontSize: 9, color: '#3a5a7a', fontFamily: 'Share Tech Mono, monospace' }}>{item.time}</span>
                    </div>
                    <div style={{ fontSize: 11, color: '#6a9abf', lineHeight: 1.4 }}>{item.body}</div>
                  </div>
                  <button onClick={() => dismiss(item.id)} style={{ background: 'none', border: 'none', color: '#3a5a7a', cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 2 }}>×</button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
