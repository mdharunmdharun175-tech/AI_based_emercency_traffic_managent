/**
 * useWebSocket — connects to the FastAPI /ws endpoint and
 * provides real-time system updates to every page.
 */
import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export function useWebSocket() {
  const ws = useRef(null)
  const [connected, setConnected]           = useState(false)
  const [lastMessage, setLastMessage]       = useState(null)
  const [ambulanceDetected, setAmbulance]   = useState(false)
  const [signalStates, setSignalStates]     = useState([])
  const [vehicleCount, setVehicleCount]     = useState(0)
  const [activeCorridors, setCorridors]     = useState(0)

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(WS_URL)

      ws.current.onopen = () => {
        setConnected(true)
        console.log('🔌 WebSocket connected')
        // heartbeat
        setInterval(() => ws.current?.send(JSON.stringify({ type: 'ping' })), 25000)
      }

      ws.current.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          setLastMessage(data)

          if (data.type === 'status_update') {
            setAmbulance(data.ambulance_detected)
            setSignalStates(data.signal_states || [])
            setVehicleCount(data.total_vehicles || 0)
            setCorridors(data.active_corridors || 0)
          }
        } catch { /* ignore */ }
      }

      ws.current.onclose = () => {
        setConnected(false)
        console.warn('🔌 WebSocket disconnected, reconnecting in 3s…')
        setTimeout(connect, 3000)
      }

      ws.current.onerror = () => ws.current?.close()
    } catch (err) {
      console.error('WebSocket error:', err)
      setTimeout(connect, 5000)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => ws.current?.close()
  }, [connect])

  const send = useCallback((data) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, lastMessage, ambulanceDetected, signalStates, vehicleCount, activeCorridors, send }
}
