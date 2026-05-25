import { useCallback, useEffect, useRef, useState } from 'react'
import { postDriveCommand, postSpeedCommand } from './lib/api'
import {
  transcriptToCommand,
  type DriveCmd,
  type SpeedLevel,
  type VoiceCmd,
  SPEED_ORDER,
} from './lib/commands'
import './App.css'

function getSpeechRecognition(): SpeechRecognition | null {
  const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition
  return Ctor ? new Ctor() : null
}

const CMD_LABEL: Record<DriveCmd, string> = {
  forward: 'Forward',
  backward: 'Back',
  left: 'Left',
  right: 'Right',
  stop: 'Stop',
}

const SPEEDS: SpeedLevel[] = ['LOW', 'MED', 'HIGH']

export default function App() {
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [lastCmd, setLastCmd] = useState<DriveCmd | null>(null)
  const [lastSend, setLastSend] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [speed, setSpeed] = useState<SpeedLevel>('MED')

  const recRef = useRef<SpeechRecognition | null>(null)
  // Time-based dedup: same command is ignored if it fired within 800ms
  const lastVoiceRef = useRef<{ cmd: string; time: number } | null>(null)
  // Always-current speed for use inside callbacks without stale closure
  const speedRef = useRef<SpeedLevel>('MED')
  useEffect(() => { speedRef.current = speed }, [speed])

  const sendCmd = useCallback(async (cmd: DriveCmd, source: string) => {
    setError('')
    setLastCmd(cmd)
    try {
      const res = await postDriveCommand(cmd)
      if (!res.ok) {
        setLastSend('')
        setError(`API ${res.status}: ${res.detail}`)
        return
      }
      setLastSend(`${source} → ${cmd} ✓`)
    } catch (e) {
      setLastSend('')
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const sendSpeed = useCallback(async (s: SpeedLevel) => {
    setError('')
    try {
      const res = await postSpeedCommand(s)
      if (!res.ok) {
        setError(`API ${res.status}: ${res.detail}`)
        return
      }
      setSpeed(s)
      setLastSend(`speed → ${s} ✓`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const handleVoiceCmd = useCallback((cmd: VoiceCmd) => {
    // Debounce: same command can't fire more than once per 800ms
    const now = Date.now()
    if (lastVoiceRef.current?.cmd === cmd && now - lastVoiceRef.current.time < 800) return
    lastVoiceRef.current = { cmd, time: now }

    if (cmd === 'speed_up' || cmd === 'speed_down') {
      const idx = SPEED_ORDER.indexOf(speedRef.current)
      const next = cmd === 'speed_up' ? Math.min(idx + 1, 2) : Math.max(idx - 1, 0)
      if (next !== idx) void sendSpeed(SPEED_ORDER[next])
    } else {
      void sendCmd(cmd, 'voice')
    }
  }, [sendCmd, sendSpeed])

  useEffect(() => {
    if (!listening) {
      recRef.current?.stop()
      recRef.current = null
      return
    }

    const rec = getSpeechRecognition()
    if (!rec) {
      setError('Speech recognition not available. Use Chrome/Edge or the D-pad below.')
      setListening(false)
      return
    }

    rec.lang = 'en-US'
    rec.continuous = true
    rec.interimResults = true

    rec.onresult = (ev: SpeechRecognitionEvent) => {
      let finalText = ''
      let interimText = ''
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        const piece = ev.results[i]?.[0]?.transcript ?? ''
        if (ev.results[i]?.isFinal) finalText += piece
        else interimText += piece
      }
      setTranscript((finalText || interimText).trim())
      if (!finalText.trim()) return
      const cmd = transcriptToCommand(finalText)
      if (cmd) handleVoiceCmd(cmd)
    }

    rec.onerror = (ev: SpeechRecognitionErrorEvent) => {
      if (ev.error === 'no-speech' || ev.error === 'aborted') return
      setError(`Mic: ${ev.error}${ev.message ? ` (${ev.message})` : ''}`)
    }

    rec.onend = () => {
      if (listening) {
        try { rec.start() } catch { /* ignore restart races */ }
      }
    }

    recRef.current = rec
    try {
      rec.start()
    } catch {
      setError('Could not start microphone. Check permissions.')
      setListening(false)
    }

    return () => {
      rec.onresult = null
      rec.onerror = null
      rec.onend = null
      try { rec.stop() } catch { /* ignore */ }
      recRef.current = null
    }
  }, [listening, handleVoiceCmd])

  return (
    <div className="app">
      <header className="header">
        <h1>EE427 · Voice Robot</h1>
        <p className="sub">Group G-19 · ESP32 bridge via FastAPI + ngrok</p>
      </header>

      <section className="panel">
        <h2>Voice</h2>
        <p className="hint">
          Say: <strong>forward</strong> / <strong>front</strong> &nbsp;·&nbsp;
          <strong>back</strong> / <strong>backward</strong> &nbsp;·&nbsp;
          <strong>left</strong> &nbsp;·&nbsp; <strong>right</strong> &nbsp;·&nbsp;
          <strong>stop</strong> &nbsp;·&nbsp;
          <strong>faster</strong> / <strong>slower</strong>
        </p>
        <button
          type="button"
          className={listening ? 'btn btn-danger' : 'btn btn-primary'}
          onClick={() => {
            setError('')
            lastVoiceRef.current = null
            setListening((v) => !v)
          }}
        >
          {listening ? 'Stop listening' : 'Start listening'}
        </button>
        <div className="transcript" aria-live="polite">
          {transcript || (listening ? 'Listening…' : '—')}
        </div>
      </section>

      <section className="panel">
        <h2>Manual (D-pad)</h2>
        <div className="dpad">
          <div className="dpad-row">
            <span className="dpad-spacer" />
            <button type="button" className="btn pad" onClick={() => void sendCmd('forward', 'pad')}>
              ▲ {CMD_LABEL.forward}
            </button>
            <span className="dpad-spacer" />
          </div>
          <div className="dpad-row">
            <button type="button" className="btn pad" onClick={() => void sendCmd('left', 'pad')}>
              ◀ {CMD_LABEL.left}
            </button>
            <button type="button" className="btn pad" onClick={() => void sendCmd('stop', 'pad')}>
              ⏹ {CMD_LABEL.stop}
            </button>
            <button type="button" className="btn pad" onClick={() => void sendCmd('right', 'pad')}>
              {CMD_LABEL.right} ▶
            </button>
          </div>
          <div className="dpad-row">
            <span className="dpad-spacer" />
            <button type="button" className="btn pad" onClick={() => void sendCmd('backward', 'pad')}>
              ▼ {CMD_LABEL.backward}
            </button>
            <span className="dpad-spacer" />
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Speed</h2>
        <div className="speed-row">
          {SPEEDS.map((s) => (
            <button
              key={s}
              type="button"
              className={`btn speed-btn${speed === s ? ' speed-active' : ''}`}
              onClick={() => void sendSpeed(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </section>

      <section className="panel status">
        <div>
          <span className="label">Last command</span>{' '}
          <strong>{lastCmd ? CMD_LABEL[lastCmd] : '—'}</strong>
        </div>
        <div className="last-send">{lastSend}</div>
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}
      </section>
    </div>
  )
}
