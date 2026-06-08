import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/',          label: 'Live Dashboard',  icon: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z' },
  { to: '/cameras',   label: 'Camera Feeds',    icon: 'M23 7l-7 5 7 5V7zM1 5h15a2 2 0 012 2v10a2 2 0 01-2 2H1a2 2 0 01-2-2V7a2 2 0 012-2z' },
  { to: '/gps',       label: 'GPS Tracking',    icon: 'M12 2a8 8 0 00-8 8c0 5.4 7.4 12.5 7.7 12.8a.5.5 0 00.6 0C12.6 22.5 20 15.4 20 10a8 8 0 00-8-8zm0 11a3 3 0 110-6 3 3 0 010 6z' },
  { to: '/signals',   label: 'Signal Control',  icon: 'M2 20h.01M7 20v-4M12 20v-8M17 20V8M22 4v16' },
  { to: '/analytics', label: 'Analytics',       icon: 'M18 20V10M12 20V4M6 20v-6' },
  { to: '/settings',  label: 'Settings',        icon: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z' },
]

const s = {
  sidebar:  { width: 220, background: '#070d14', borderRight: '1px solid #0d2035', display: 'flex', flexDirection: 'column', flexShrink: 0 },
  logo:     { padding: '20px 16px', borderBottom: '1px solid #0d2035', display: 'flex', alignItems: 'center', gap: 10 },
  logoBox:  { width: 36, height: 36, background: '#00e5ff15', border: '1px solid #00e5ff40', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  logoText: { fontFamily: 'Rajdhani, sans-serif', fontSize: 13, fontWeight: 700, color: '#00e5ff', letterSpacing: 1, lineHeight: 1.2 },
  nav:      { flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2 },
  statusBox:{ margin: 12, padding: 12, background: '#041a10', border: '1px solid #0d4020', borderRadius: 10 },
  statusLbl:{ fontSize: 10, fontWeight: 700, color: '#00ff88', letterSpacing: 2, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 5 },
  statusDot:{ width: 6, height: 6, background: '#00ff88', borderRadius: '50%' },
  statusTxt:{ fontSize: 11, color: '#4a8a6a', lineHeight: 1.5 },
}

export default function Sidebar() {
  return (
    <div style={s.sidebar}>
      <div style={s.logo}>
        <div style={s.logoBox}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00e5ff" strokeWidth="2">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/><circle cx="12" cy="10" r="3"/>
          </svg>
        </div>
        <div style={s.logoText}>AI TRAFFIC<br/>SYS v1.0</div>
      </div>

      <nav style={s.nav}>
        {NAV.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
              fontWeight: 500, letterSpacing: 0.3, textDecoration: 'none',
              color: isActive ? '#00e5ff' : '#4a6a8a',
              background: isActive ? '#0d2a40' : 'transparent',
              borderLeft: isActive ? '2px solid #00e5ff' : '2px solid transparent',
              transition: 'all 0.2s',
            })}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d={item.icon}/>
            </svg>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={s.statusBox}>
        <div style={s.statusLbl}>
          <div style={{ ...s.statusDot, animation: 'pulse-dot 1.4s ease-in-out infinite' }} className="animate-pulse-dot"/>
          SYSTEM ACTIVE
        </div>
        <div style={s.statusTxt}>AI model online. Multi-modal detection synchronized.</div>
      </div>
    </div>
  )
}
