import type { DriveCmd, SpeedLevel } from './commands'

function apiBase(): string {
  const raw = import.meta.env.VITE_API_URL?.trim()
  if (!raw) throw new Error('Missing VITE_API_URL')
  return raw.replace(/\/$/, '')
}

function apiKey(): string {
  const k = import.meta.env.VITE_API_KEY?.trim()
  if (!k) throw new Error('Missing VITE_API_KEY')
  return k
}

function headers(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'X-Api-Key': apiKey(),
    'ngrok-skip-browser-warning': '69420',
  }
}

export type ApiResponse = { ok: true; data: unknown } | { ok: false; status: number; detail: string }

async function post(path: string, body: unknown): Promise<ApiResponse> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  })
  const text = await res.text()
  let parsed: unknown = text
  try { parsed = JSON.parse(text) } catch { /* plain text */ }
  if (!res.ok) {
    const detail =
      typeof parsed === 'object' && parsed !== null && 'detail' in parsed
        ? String((parsed as { detail: unknown }).detail)
        : text || res.statusText
    return { ok: false, status: res.status, detail }
  }
  return { ok: true, data: parsed }
}

export function postDriveCommand(cmd: DriveCmd): Promise<ApiResponse> {
  return post('/api/command', { cmd })
}

export function postSpeedCommand(speed: SpeedLevel): Promise<ApiResponse> {
  return post('/api/speed', { speed })
}
