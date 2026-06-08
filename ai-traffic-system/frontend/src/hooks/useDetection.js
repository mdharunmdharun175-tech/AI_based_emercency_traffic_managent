/**
 * useDetection — uploads camera frames to /api/detect
 * and returns latest detection results.
 *
 * Usage:
 *   const { result, detecting, triggerDetect } = useDetection()
 *   // Call triggerDetect(blob) whenever you have a frame blob
 */
import { useState, useCallback, useRef } from 'react'
import { detectStream } from '../utils/api'

export function useDetection(onAmbulanceDetected) {
  const [result, setResult]         = useState(null)
  const [detecting, setDetecting]   = useState(false)
  const [error, setError]           = useState(null)
  const lastAmbulance = useRef(false)

  const triggerDetect = useCallback(async (imageBlob) => {
    if (detecting) return   // skip frame if previous still processing
    setDetecting(true)
    setError(null)

    try {
      const form = new FormData()
      form.append('file', imageBlob, 'frame.jpg')
      const res = await detectStream(form)
      const data = res.data
      setResult(data)

      // Fire callback once when ambulance first appears
      if (data.ambulance_detected && !lastAmbulance.current) {
        onAmbulanceDetected?.(data)
      }
      lastAmbulance.current = data.ambulance_detected
    } catch (err) {
      setError(err.message)
    } finally {
      setDetecting(false)
    }
  }, [detecting, onAmbulanceDetected])

  return { result, detecting, error, triggerDetect }
}
