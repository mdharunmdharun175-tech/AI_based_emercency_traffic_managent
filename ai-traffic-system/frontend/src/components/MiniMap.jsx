/**
 * MiniMap — lightweight grid-based GPS map visualization.
 * No external map library required.
 * Accepts a list of vehicle positions and renders dots on a grid.
 */
import { useRef, useEffect } from 'react'

// Rough Bengaluru bounding box for normalization
const LAT_MIN = 12.85, LAT_MAX = 13.10
const LNG_MIN = 77.45, LNG_MAX = 77.75

function latLngToXY(lat, lng, W, H) {
  const x = ((lng - LNG_MIN) / (LNG_MAX - LNG_MIN)) * W
  const y = H - ((lat - LAT_MIN) / (LAT_MAX - LAT_MIN)) * H  // invert Y
  return [x, y]
}

export default function MiniMap({ vehicles = [], width = '100%', height = 120 }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height

    // Background
    ctx.fillStyle = '#030810'
    ctx.fillRect(0, 0, W, H)

    // Grid
    ctx.strokeStyle = '#0d203518'
    ctx.lineWidth = 0.5
    for (let x = 0; x < W; x += 30) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke()
    }
    for (let y = 0; y < H; y += 30) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke()
    }

    // Road lines (simplified)
    ctx.strokeStyle = '#0d2540'; ctx.lineWidth = 2
    ctx.beginPath(); ctx.moveTo(W * 0.3, 0); ctx.lineTo(W * 0.3, H); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(W * 0.6, 0); ctx.lineTo(W * 0.6, H); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(0, H * 0.4); ctx.lineTo(W, H * 0.4); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(0, H * 0.65); ctx.lineTo(W, H * 0.65); ctx.stroke()

    // Draw ambulance route (dashed line connecting ambulances)
    const ambulances = vehicles.filter(v => v.is_emergency)
    if (ambulances.length >= 2) {
      ctx.strokeStyle = '#00e5ff44'; ctx.lineWidth = 1; ctx.setLineDash([4, 4])
      ctx.beginPath()
      ambulances.forEach((v, i) => {
        const [x, y] = latLngToXY(v.latitude, v.longitude, W, H)
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
      })
      ctx.stroke(); ctx.setLineDash([])
    }

    // Draw vehicles
    vehicles.forEach(v => {
      const [x, y] = latLngToXY(v.latitude, v.longitude, W, H)
      const isAmb = v.is_emergency
      const color = isAmb ? '#00e5ff' : '#4488ff'
      const r = isAmb ? 6 : 4

      // Glow
      ctx.beginPath()
      ctx.arc(x, y, r + 4, 0, Math.PI * 2)
      ctx.fillStyle = color + '22'
      ctx.fill()

      // Dot
      ctx.beginPath()
      ctx.arc(x, y, r, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()

      // Label
      if (isAmb) {
        ctx.fillStyle = '#00e5ffcc'
        ctx.font = '9px Share Tech Mono'
        ctx.fillText(v.vehicle_id || 'AMB', x + 8, y - 4)
      }
    })
  }, [vehicles])

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={height}
      style={{ width, height, display: 'block', borderRadius: 6 }}
    />
  )
}
