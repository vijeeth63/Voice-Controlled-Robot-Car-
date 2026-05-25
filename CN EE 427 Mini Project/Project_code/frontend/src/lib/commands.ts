export type DriveCmd = 'forward' | 'backward' | 'left' | 'right' | 'stop'
export type SpeedCmd = 'speed_up' | 'speed_down'
export type VoiceCmd = DriveCmd | SpeedCmd

export type SpeedLevel = 'LOW' | 'MED' | 'HIGH'
export const SPEED_ORDER: SpeedLevel[] = ['LOW', 'MED', 'HIGH']

export function transcriptToCommand(text: string): VoiceCmd | null {
  const t = text.toLowerCase()
  // Check stop first to avoid matching inside other words
  if (/\bstop\b/.test(t)) return 'stop'
  if (/\b(backward|back)\b/.test(t)) return 'backward'
  if (/\bleft\b/.test(t)) return 'left'
  if (/\bright\b/.test(t)) return 'right'
  if (/\b(forward|front)\b/.test(t)) return 'forward'
  if (/\b(faster|fast)\b/.test(t)) return 'speed_up'
  if (/\b(slower|slow)\b/.test(t)) return 'speed_down'
  return null
}
