import { useState, useEffect } from 'react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const genHourly = () => Array.from({ length: 24 }, (_, h) => ({
  hour: `${h}:00`,
  vehicles: Math.floor(40 + Math.random() * 160),
  ambulances: Math.floor(Math.random() * 3),
  congestion: Math.floor(20 + Math.random() * 80),
}))

const SUMMARY = [
  { label: 'Vehicles Today',       value: '1,842', accent: '#00e5ff' },
  { label: 'Ambulances Detected',  value: '7',     accent: '#ff4444' },
  { label: 'Corridors Activated',  value: '7',     accent: '#00ff88' },
  { label: 'Avg Clear Time',       value: '18.4s', accent: '#ffaa00' },
  { label: 'Success Rate',         value: '98.6%', accent: '#4488ff' },
  { label: 'Siren Detections',     value: '5',     accent: '#aa88ff' },
]

const tipStyle = { background: '#0d1a28', border: '1px solid #0d2035', color: '#c8d8e8', fontSize: 11 }

export default function Analytics() {
  const [data, setData] = useState(genHourly())
  useEffect(() => { const t = setInterval(() => setData(genHourly()), 10000); return () => clearInterval(t) }, [])

  return (
    <div style={{ padding: '14px 20px', height: '100%', display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto' }}>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10 }}>
        {SUMMARY.map(s => (
          <div key={s.label} style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 10, padding: '12px 14px' }}>
            <div style={{ fontSize: 9, color: '#3a5a7a', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 24, fontWeight: 700, color: s.accent }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>

        {/* Vehicle volume area chart */}
        <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 12 }}>VEHICLE VOLUME (24H)</div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="vGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00e5ff" stopOpacity={0.25}/>
                  <stop offset="95%" stopColor="#00e5ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#0d2035" />
              <XAxis dataKey="hour" tick={{ fill: '#3a5a7a', fontSize: 9 }} interval={3} />
              <YAxis tick={{ fill: '#3a5a7a', fontSize: 9 }} />
              <Tooltip contentStyle={tipStyle} />
              <Area type="monotone" dataKey="vehicles" stroke="#00e5ff" fill="url(#vGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Congestion bar chart */}
        <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 12 }}>CONGESTION LEVEL (24H)</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0d2035" />
              <XAxis dataKey="hour" tick={{ fill: '#3a5a7a', fontSize: 9 }} interval={3} />
              <YAxis tick={{ fill: '#3a5a7a', fontSize: 9 }} />
              <Tooltip contentStyle={tipStyle} />
              <Bar dataKey="congestion" fill="#ff444455" stroke="#ff4444" strokeWidth={1} radius={[2,2,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Ambulance detections */}
      <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 16 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 12 }}>AMBULANCE DETECTIONS (24H)</div>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#0d2035" />
            <XAxis dataKey="hour" tick={{ fill: '#3a5a7a', fontSize: 9 }} interval={3} />
            <YAxis tick={{ fill: '#3a5a7a', fontSize: 9 }} allowDecimals={false} />
            <Tooltip contentStyle={tipStyle} />
            <Bar dataKey="ambulances" fill="#00e5ff55" stroke="#00e5ff" strokeWidth={1} radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Recent detections table */}
      <div style={{ background: '#070d14', border: '1px solid #0d2035', borderRadius: 12, padding: 16 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#3a5a7a', letterSpacing: 2, marginBottom: 12 }}>RECENT DETECTIONS</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #0d2035' }}>
              {['Time', 'Type', 'Plate', 'Lane', 'Confidence', 'Action'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 10px', color: '#3a5a7a', fontSize: 10, letterSpacing: 1 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 8 }, (_, i) => {
              const isAmb = i % 4 === 0
              return (
                <tr key={i} style={{ borderBottom: '1px solid #0a1520' }}>
                  <td style={{ padding: '7px 10px', fontFamily: 'Share Tech Mono, monospace', color: '#3a5a7a', fontSize: 10 }}>
                    {new Date(Date.now() - i * 45000).toLocaleTimeString()}
                  </td>
                  <td style={{ padding: '7px 10px', color: isAmb ? '#ff4444' : '#4488ff', fontWeight: 600 }}>{isAmb ? 'Ambulance' : 'Car'}</td>
                  <td style={{ padding: '7px 10px', fontFamily: 'Share Tech Mono, monospace', color: '#6a9abf', fontSize: 10 }}>
                    {isAmb ? `KA-05-MK-${4000 + i}` : '—'}
                  </td>
                  <td style={{ padding: '7px 10px', color: '#4a6a8a' }}>L{(i % 4) + 1}</td>
                  <td style={{ padding: '7px 10px', color: '#00ff88' }}>{(0.86 + Math.random() * 0.13).toFixed(3)}</td>
                  <td style={{ padding: '7px 10px', color: isAmb ? '#00e5ff' : '#3a5a7a', fontSize: 10 }}>
                    {isAmb ? 'CORRIDOR ACTIVATED' : 'Logged'}
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
