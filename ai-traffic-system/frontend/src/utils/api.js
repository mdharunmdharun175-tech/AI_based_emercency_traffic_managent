import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const api = axios.create({ baseURL: BASE, timeout: 15000 })

// ── Detection ──────────────────────────────────────────────
export const detectVehicles = (formData) =>
  api.post('/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } })

export const detectStream = (formData) =>
  api.post('/detect/stream', formData, { headers: { 'Content-Type': 'multipart/form-data' } })

// ── Signals ────────────────────────────────────────────────
export const getSignals       = ()           => api.get('/signal-control')
export const activateCorridor = (laneId, dur) => api.post(`/signal-control/corridor/${laneId}?duration=${dur}`)
export const overrideSignal   = (payload)    => api.post('/signal-control/override', payload)
export const resetSignals     = ()           => api.post('/signal-control/reset')

// ── GPS ───────────────────────────────────────────────────
export const getGPS    = ()         => api.get('/gps-data')
export const updateGPS = (payload)  => api.post('/gps-data', payload)

// ── Analytics ─────────────────────────────────────────────
export const getAnalyticsSummary    = () => api.get('/analytics/summary')
export const getCongestionTimeline  = () => api.get('/analytics/congestion')
export const getRecentDetections    = (limit = 50) => api.get(`/analytics/detections?limit=${limit}`)

// ── System ────────────────────────────────────────────────
export const getSystemStatus = () => api.get('/status', { baseURL: 'http://localhost:8000' })

export default api
