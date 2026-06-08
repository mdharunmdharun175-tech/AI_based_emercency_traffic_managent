import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import EmergencyBanner from './components/EmergencyBanner'
import Dashboard from './pages/Dashboard'
import CameraFeeds from './pages/CameraFeeds'
import GPSTracking from './pages/GPSTracking'
import SignalControl from './pages/SignalControl'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import { useWebSocket } from './hooks/useWebSocket'

export default function App() {
  const ws = useWebSocket()

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#050a0f', overflow: 'hidden' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Topbar ws={ws} />
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <Routes>
            <Route path="/"          element={<Dashboard ws={ws} />} />
            <Route path="/cameras"   element={<CameraFeeds ws={ws} />} />
            <Route path="/gps"       element={<GPSTracking />} />
            <Route path="/signals"   element={<SignalControl ws={ws} />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/settings"  element={<Settings />} />
            <Route path="*"          element={<Navigate to="/" />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}
