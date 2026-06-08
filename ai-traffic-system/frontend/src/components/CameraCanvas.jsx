import { useEffect, useRef } from 'react'

const VEHICLES_INIT = [
  { id:1, x:120,  y:200, w:70, h:45, type:'car',       color:'#4488ff', conf:0.95, speed:0.6 },
  { id:2, x:280,  y:160, w:75, h:50, type:'bus',       color:'#aa88ff', conf:0.96, speed:0.3 },
  { id:3, x:420,  y:220, w:65, h:40, type:'car',       color:'#4488ff', conf:0.92, speed:0.7 },
  { id:4, x:550,  y:180, w:70, h:42, type:'truck',     color:'#ffaa44', conf:0.90, speed:0.4 },
  { id:5, x:680,  y:240, w:68, h:44, type:'car',       color:'#4488ff', conf:0.88, speed:0.65 },
  { id:6, x:180,  y:310, w:68, h:44, type:'car',       color:'#4488ff', conf:0.91, speed:0.55 },
  { id:7, x:360,  y:290, w:90, h:55, type:'ambulance', color:'#00e5ff', conf:0.98, speed:0.5, isAmb:true },
  { id:8, x:490,  y:320, w:66, h:42, type:'car',       color:'#4488ff', conf:0.87, speed:0.70 },
  { id:9, x:620,  y:300, w:70, h:45, type:'car',       color:'#4488ff', conf:0.93, speed:0.60 },
]

export default function CameraCanvas({ style }) {
  const canvasRef = useRef(null)
  const animRef   = useRef(null)
  const vehs      = useRef(VEHICLES_INIT.map(v => ({ ...v })))

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let tick = 0

    const draw = () => {
      canvas.width  = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
      const W = canvas.width, H = canvas.height

      ctx.fillStyle = '#030810'
      ctx.fillRect(0, 0, W, H)

      // Lane bands
      const laneH = H / 5
      for (let i = 0; i < 5; i++) {
        ctx.fillStyle = i % 2 === 0 ? '#080e18' : '#06111c'
        ctx.fillRect(0, i * laneH, W, laneH)
      }

      // Lane dividers
      ctx.strokeStyle = '#1a3050'; ctx.lineWidth = 1; ctx.setLineDash([20, 15])
      for (let i = 1; i < 5; i++) {
        ctx.beginPath(); ctx.moveTo(0, i * laneH); ctx.lineTo(W, i * laneH); ctx.stroke()
      }
      ctx.setLineDash([])

      // Grid
      ctx.strokeStyle = '#0d203508'; ctx.lineWidth = 0.5
      for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke() }

      // Vehicles
      vehs.current.forEach(v => {
        v.x -= v.speed
        if (v.x + v.w < -20) v.x = W + 20

        const sx = W / 800, sy = H / 420
        const rx = v.x * sx, ry = v.y * sy, rw = v.w * sx, rh = v.h * sy

        if (v.isAmb) {
          const glow = Math.sin(tick * 0.08) * 0.5 + 0.5
          ctx.shadowBlur = 20 + glow * 15; ctx.shadowColor = '#00e5ff'
          ctx.strokeStyle = `rgba(0,229,255,${0.5 + glow * 0.5})`; ctx.lineWidth = 2.5
          ctx.strokeRect(rx - 3, ry - 3, rw + 6, rh + 6)
          ctx.shadowBlur = 0

          ctx.fillStyle = '#00e5ff18'; ctx.fillRect(rx, ry, rw, rh)
          ctx.strokeStyle = '#00e5ff'; ctx.lineWidth = 2; ctx.strokeRect(rx, ry, rw, rh)

          ctx.fillStyle = '#00e5ffee'; ctx.font = `bold ${Math.max(10, 11 * sx)}px Exo 2`
          ctx.fillText('AMBULANCE', rx, ry - 18 * sy)
          ctx.fillStyle = '#00bbdd'; ctx.font = `${Math.max(9, 10 * sx)}px Share Tech Mono`
          ctx.fillText('(0.98)', rx, ry - 6 * sy)

          const cx = rx + rw / 2, cy = ry + rh / 2
          ctx.fillStyle = '#00e5ff'
          ctx.fillRect(cx - 3 * sx, cy - 8 * sy, 6 * sx, 16 * sy)
          ctx.fillRect(cx - 8 * sx, cy - 3 * sy, 16 * sx, 6 * sy)

          ctx.strokeStyle = `rgba(0,229,255,${0.3 * (Math.sin(tick * 0.2) * 0.5 + 0.5)})`
          ctx.lineWidth = 1; ctx.beginPath()
          ctx.arc(cx, cy, (30 + tick % 30) * sx, 0, Math.PI * 2); ctx.stroke()
        } else {
          ctx.fillStyle = v.color + '22'; ctx.fillRect(rx, ry, rw, rh)
          ctx.strokeStyle = v.color + '88'; ctx.lineWidth = 1.5; ctx.strokeRect(rx, ry, rw, rh)
          ctx.fillStyle = v.color + 'cc'; ctx.font = `bold ${Math.max(9, 10 * sx)}px Exo 2`
          ctx.fillText(v.type, rx + 2, ry - 4 * sy)
          ctx.fillStyle = v.color + '99'; ctx.font = `${Math.max(8, 9 * sx)}px monospace`
          ctx.fillText(`${v.conf}`, rx + rw - 24 * sx, ry - 4 * sy)
        }
      })

      // Scan line
      ctx.fillStyle = '#00e5ff08'; ctx.fillRect(0, (tick * 2) % H, W, 2)

      // HUD bar
      ctx.fillStyle = '#00e5ff22'; ctx.fillRect(0, 0, W, 22)
      ctx.fillStyle = '#00e5ff88'; ctx.font = "10px 'Share Tech Mono'"
      ctx.fillText('CAM-01  |  AI: ACTIVE  |  FPS: 30  |  RES: 1920×1080  |  YOLOv8', 8, 15)

      tick++
      animRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animRef.current)
  }, [])

  return <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block', ...style }} />
}
