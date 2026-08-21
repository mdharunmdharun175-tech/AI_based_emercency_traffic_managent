import { useState } from 'react'

export default function PriorityQueueWidget({ priorityQueue = [], activeEmergencyLane = '' }) {
  if (!priorityQueue || priorityQueue.length === 0) {
    return (
      <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 14 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 8 }}>
          Multi-Feature Emergency Priority Queue
        </div>
        <div style={{ padding: '16px 10px', textAlign: 'center', color: '#2a4a6a', fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}>
          NO ACTIVE AMBULANCES IN QUEUE
        </div>
      </div>
    )
  }

  return (
    <div style={{ background: '#070d14', border: '1px solid #ff444444', borderRadius: 12, padding: 14, boxShadow: '0 0 15px #ff000015' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#ff4444', letterSpacing: 2, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, background: '#ff4444', borderRadius: '50%', boxShadow: '0 0 8px #ff4444' }} />
          Multi-Feature Priority Queue ({priorityQueue.length} Active)
        </div>
        <span style={{ fontSize: 9, color: '#00e5ff', fontFamily: 'Share Tech Mono, monospace' }}>
          SORTED: DISTANCE → ETA → COMBINED CONF
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #0d2035', color: '#4a6a8a', textAlign: 'left' }}>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>RANK</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>ID / LANE</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>COMBINED CONF</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>ROOF LIGHTS</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>TEXT</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>SYMBOL</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>PLATE</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>DIST / ETA</th>
              <th style={{ padding: '6px 4px', fontSize: 8 }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {priorityQueue.map((item, index) => {
              const isServing = index === 0
              const combinedPct = Math.round((item.combined_score || item.confidence || 0.88) * 100)
              const hasRoof = item.roof_lights_detected !== false
              const hasText = item.text_detected !== false
              const hasSymbol = item.symbol_detected !== false
              const symName = item.symbol_name || (hasSymbol ? 'Red Cross' : 'None')

              return (
                <tr
                  key={item.tracking_id || index}
                  style={{
                    borderBottom: '1px solid #0d2035',
                    background: isServing ? '#ff000015' : 'transparent',
                    color: isServing ? '#ffffff' : '#a8c8e8',
                    fontWeight: isServing ? 700 : 400,
                  }}
                >
                  <td style={{ padding: '6px 4px', color: isServing ? '#ff4444' : '#00e5ff', fontFamily: 'Share Tech Mono, monospace' }}>
                    #{index + 1} {isServing ? '👑' : ''}
                  </td>
                  <td style={{ padding: '6px 4px' }}>
                    <div style={{ fontFamily: 'Share Tech Mono, monospace', color: '#00e5ff', fontWeight: 700 }}>
                      {item.tracking_id}
                    </div>
                    <div style={{ fontSize: 9, color: '#ffaa00' }}>{item.lane_id}</div>
                  </td>
                  <td style={{ padding: '6px 4px' }}>
                    <div style={{
                      display: 'inline-block', padding: '1px 5px', borderRadius: 4,
                      background: combinedPct >= 80 ? '#00ff8820' : '#ffaa0020',
                      border: `1px solid ${combinedPct >= 80 ? '#00ff8855' : '#ffaa0055'}`,
                      color: combinedPct >= 80 ? '#00ff88' : '#ffaa00',
                      fontFamily: 'Share Tech Mono, monospace', fontWeight: 700
                    }}>
                      {combinedPct}%
                    </div>
                  </td>
                  <td style={{ padding: '6px 4px' }}>
                    <span style={{ color: hasRoof ? '#00ff88' : '#ff4444', fontSize: 9 }}>
                      {hasRoof ? '🔴🔵 ACTIVE' : '❌ NO'}
                    </span>
                  </td>
                  <td style={{ padding: '6px 4px' }}>
                    <span style={{ color: hasText ? '#00e5ff' : '#6a9abf', fontSize: 9 }}>
                      {hasText ? '✅ DETECTED' : '❌ NO'}
                    </span>
                  </td>
                  <td style={{ padding: '6px 4px' }}>
                    <span style={{ color: hasSymbol ? '#ffaa00' : '#6a9abf', fontSize: 9 }}>
                      {hasSymbol ? `✚ ${symName}` : '❌ NO'}
                    </span>
                  </td>
                  <td style={{ padding: '6px 4px', fontFamily: 'Share Tech Mono, monospace', color: '#00ff88' }}>
                    {item.plate || 'AMB-EMG'}
                  </td>
                  <td style={{ padding: '6px 4px', fontFamily: 'Share Tech Mono, monospace' }}>
                    <div style={{ color: '#ff4444' }}>{item.distance ? item.distance.toFixed(1) : '0.0'} m</div>
                    <div style={{ color: '#00ff88', fontSize: 9 }}>ETA: {item.eta ? item.eta.toFixed(1) : '0.0'} s</div>
                  </td>
                  <td style={{ padding: '6px 4px' }}>
                    <span style={{
                      padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700,
                      background: isServing ? '#ff000030' : '#00e5ff15',
                      color: isServing ? '#ff4444' : '#00e5ff',
                      border: `1px solid ${isServing ? '#ff444455' : '#00e5ff44'}`
                    }}>
                      {isServing ? '🚨 SERVING' : '⏳ QUEUED'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
