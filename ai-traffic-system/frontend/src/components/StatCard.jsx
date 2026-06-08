export default function StatCard({ label, value, delta, accent = '#00e5ff', icon }) {
  return (
    <div style={{
      background: '#070d14', border: '1px solid #0d2035', borderRadius: 12,
      padding: '14px 16px', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg, transparent, ${accent}33, transparent)` }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: `${accent}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {icon}
        </div>
        {delta && <span style={{ fontSize: 11, fontWeight: 600, color: delta.startsWith('+') ? '#00ff88' : '#ff6644' }}>{delta}</span>}
      </div>
      <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 28, fontWeight: 700, color: accent, lineHeight: 1, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 10, color: '#3a5a7a', letterSpacing: 1.5, textTransform: 'uppercase', fontWeight: 500 }}>{label}</div>
    </div>
  )
}
