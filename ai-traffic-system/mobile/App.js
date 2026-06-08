/**
 * AI Traffic System — Ambulance Driver Mobile App (React Native)
 * 
 * Features:
 *  - Real-time GPS tracking (posts position to backend every 1s)
 *  - Signal status ahead (receives via WebSocket)
 *  - Route guidance overlay
 *  - Emergency activation button
 * 
 * Setup:
 *   npx react-native init AmbulanceApp --template react-native-template-typescript
 *   Copy this file to App.js
 *   npm install @react-navigation/native react-native-maps @react-native-community/geolocation
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  StatusBar, SafeAreaView, ScrollView, Alert,
} from 'react-native';

const API_BASE = 'http://YOUR_BACKEND_IP:8000';
const WS_URL   = 'ws://YOUR_BACKEND_IP:8000/ws';
const VEHICLE_ID = 'AMB-001';

export default function App() {
  const [position, setPosition]       = useState(null);
  const [signalAhead, setSignalAhead] = useState('unknown');
  const [connected, setConnected]     = useState(false);
  const [active, setActive]           = useState(false);
  const [speed, setSpeed]             = useState(0);
  const [log, setLog]                 = useState([]);
  const ws = useRef(null);
  const gpsTimer = useRef(null);

  // WebSocket connection
  useEffect(() => {
    connectWS();
    return () => { ws.current?.close(); clearInterval(gpsTimer.current); };
  }, []);

  const connectWS = () => {
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen  = () => setConnected(true);
    ws.current.onclose = () => { setConnected(false); setTimeout(connectWS, 3000); };
    ws.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'status_update') {
          const myLane  = data.signal_states?.find(s => s.priority);
          setSignalAhead(myLane ? myLane.state : 'red');
        }
      } catch {}
    };
  };

  // GPS tracking
  const startTracking = () => {
    setActive(true);
    addLog('Emergency mode activated');

    const Geolocation = require('@react-native-community/geolocation').default;
    gpsTimer.current = setInterval(() => {
      Geolocation.getCurrentPosition(
        pos => {
          const { latitude, longitude, speed: spd } = pos.coords;
          setPosition({ latitude, longitude });
          setSpeed(Math.round((spd || 0) * 3.6));
          postGPS(latitude, longitude, spd * 3.6);
        },
        err => console.warn('GPS error:', err),
        { enableHighAccuracy: true, timeout: 2000 }
      );
    }, 1000);
  };

  const stopTracking = () => {
    setActive(false);
    clearInterval(gpsTimer.current);
    addLog('Tracking stopped');
  };

  const postGPS = async (lat, lng, spd) => {
    try {
      await fetch(`${API_BASE}/api/gps-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vehicle_id: VEHICLE_ID,
          latitude: lat,
          longitude: lng,
          speed_kmh: spd,
          timestamp: Date.now() / 1000,
          is_emergency: true,
        }),
      });
    } catch {}
  };

  const addLog = (msg) => {
    const now = new Date().toLocaleTimeString();
    setLog(prev => [`[${now}] ${msg}`, ...prev].slice(0, 20));
  };

  const signalColor = { green: '#00ff88', red: '#ff4444', unknown: '#888' };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#050a0f" />

      <View style={styles.header}>
        <Text style={styles.headerTitle}>AI TRAFFIC SYSTEM</Text>
        <Text style={styles.headerSub}>Ambulance Driver</Text>
      </View>

      {/* Signal Ahead */}
      <View style={[styles.signalCard, { borderColor: signalColor[signalAhead] + '60' }]}>
        <Text style={styles.signalLabel}>SIGNAL AHEAD</Text>
        <View style={[styles.signalDot, { backgroundColor: signalColor[signalAhead] }]} />
        <Text style={[styles.signalText, { color: signalColor[signalAhead] }]}>
          {signalAhead.toUpperCase()}
        </Text>
      </View>

      {/* Stats */}
      <View style={styles.statsRow}>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>SPEED</Text>
          <Text style={styles.statValue}>{speed}</Text>
          <Text style={styles.statUnit}>km/h</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>VEHICLE</Text>
          <Text style={[styles.statValue, { fontSize: 16 }]}>{VEHICLE_ID}</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>WS</Text>
          <Text style={[styles.statValue, { color: connected ? '#00ff88' : '#ff4444', fontSize: 14 }]}>
            {connected ? 'LIVE' : 'OFF'}
          </Text>
        </View>
      </View>

      {/* GPS */}
      {position && (
        <View style={styles.gpsBox}>
          <Text style={styles.gpsText}>
            LAT: {position.latitude.toFixed(5)}  LNG: {position.longitude.toFixed(5)}
          </Text>
        </View>
      )}

      {/* Activate button */}
      <TouchableOpacity
        style={[styles.btn, active ? styles.btnStop : styles.btnStart]}
        onPress={active ? stopTracking : startTracking}
      >
        <Text style={styles.btnText}>{active ? '⏹ STOP EMERGENCY' : '🚨 ACTIVATE EMERGENCY'}</Text>
      </TouchableOpacity>

      {/* Log */}
      <View style={styles.logBox}>
        <Text style={styles.logTitle}>EVENT LOG</Text>
        <ScrollView>
          {log.map((l, i) => (
            <Text key={i} style={styles.logLine}>{l}</Text>
          ))}
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:        { flex: 1, backgroundColor: '#050a0f' },
  header:      { padding: 16, borderBottomWidth: 1, borderBottomColor: '#0d2035' },
  headerTitle: { fontFamily: 'monospace', fontSize: 16, fontWeight: '700', color: '#00e5ff', letterSpacing: 2 },
  headerSub:   { fontSize: 12, color: '#3a5a7a', marginTop: 2 },
  signalCard:  { margin: 16, padding: 20, borderWidth: 1, borderRadius: 12, backgroundColor: '#070d14', alignItems: 'center' },
  signalLabel: { fontSize: 10, color: '#3a5a7a', letterSpacing: 2, marginBottom: 10 },
  signalDot:   { width: 40, height: 40, borderRadius: 20, marginBottom: 10 },
  signalText:  { fontSize: 22, fontWeight: '700', letterSpacing: 2 },
  statsRow:    { flexDirection: 'row', marginHorizontal: 16, gap: 10 },
  statBox:     { flex: 1, backgroundColor: '#070d14', borderWidth: 1, borderColor: '#0d2035', borderRadius: 10, padding: 12, alignItems: 'center' },
  statLabel:   { fontSize: 9, color: '#3a5a7a', letterSpacing: 1.5, marginBottom: 4 },
  statValue:   { fontSize: 20, fontWeight: '700', color: '#00e5ff', fontFamily: 'monospace' },
  statUnit:    { fontSize: 10, color: '#3a5a7a' },
  gpsBox:      { margin: 16, padding: 10, backgroundColor: '#070d14', borderRadius: 8, borderWidth: 1, borderColor: '#0d2035' },
  gpsText:     { fontFamily: 'monospace', fontSize: 11, color: '#3a5a7a', textAlign: 'center' },
  btn:         { margin: 16, padding: 16, borderRadius: 12, alignItems: 'center' },
  btnStart:    { backgroundColor: '#ff000025', borderWidth: 1, borderColor: '#ff444466' },
  btnStop:     { backgroundColor: '#00e5ff15', borderWidth: 1, borderColor: '#00e5ff66' },
  btnText:     { fontSize: 14, fontWeight: '700', color: '#fff', letterSpacing: 1 },
  logBox:      { flex: 1, margin: 16, backgroundColor: '#070d14', borderRadius: 10, borderWidth: 1, borderColor: '#0d2035', padding: 12 },
  logTitle:    { fontSize: 9, color: '#3a5a7a', letterSpacing: 2, marginBottom: 8 },
  logLine:     { fontFamily: 'monospace', fontSize: 10, color: '#4a6a8a', marginBottom: 3 },
});
