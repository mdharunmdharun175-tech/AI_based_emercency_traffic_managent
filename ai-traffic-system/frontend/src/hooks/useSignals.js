/**
 * useSignals — fetches signal states and provides control actions.
 */
import { useState, useEffect, useCallback } from 'react'
import { getSignals, overrideSignal, activateCorridor, resetSignals } from '../utils/api'

export function useSignals(wsSignalStates) {
  const [lanes, setLanes]     = useState([])
  const [loading, setLoading] = useState(false)

  // Prefer real-time WebSocket states when available
  useEffect(() => {
    if (wsSignalStates && wsSignalStates.length > 0) {
      setLanes(wsSignalStates)
    }
  }, [wsSignalStates])

  // Initial fetch
  useEffect(() => {
    fetchSignals()
  }, [])

  const fetchSignals = useCallback(async () => {
    try {
      const res = await getSignals()
      setLanes(res.data.lanes || [])
    } catch {
      // WebSocket will keep states updated — REST is best-effort here
    }
  }, [])

  const override = useCallback(async (laneId, state) => {
    setLoading(true)
    try {
      await overrideSignal({ lane_id: laneId, state, duration_seconds: 30 })
      setLanes(prev => prev.map(l => l.lane_id === laneId ? { ...l, state } : l))
    } catch (e) {
      console.error('Signal override failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const corridor = useCallback(async (laneId, duration = 30) => {
    setLoading(true)
    try {
      await activateCorridor(laneId, duration)
      setLanes(prev => prev.map(l => ({ ...l, state: l.lane_id === laneId ? 'green' : 'red' })))
    } catch (e) {
      console.error('Corridor activation failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(async () => {
    setLoading(true)
    try {
      await resetSignals()
      await fetchSignals()
    } finally {
      setLoading(false)
    }
  }, [fetchSignals])

  return { lanes, loading, override, corridor, reset, refetch: fetchSignals }
}
