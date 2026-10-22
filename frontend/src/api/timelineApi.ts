import type { TimelineDay } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
export class TimelineApiError extends Error {
  constructor(message: string) { super(message); this.name = 'TimelineApiError' }
}
export const timelineApi = {
  async getDay(date: string): Promise<TimelineDay> {
    const response = await fetch(`${apiBaseUrl}/api/timeline?date=${encodeURIComponent(date)}`)
    if (!response.ok) {
      let message = `Timeline request failed with status ${response.status}`
      try { const body = await response.json() as { detail?: string }; if (body.detail) message = body.detail } catch { /* keep status message */ }
      throw new TimelineApiError(message)
    }
    return response.json() as Promise<TimelineDay>
  },
}
