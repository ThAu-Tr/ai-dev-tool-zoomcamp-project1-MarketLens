import type { Industry } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export class IndustryApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'IndustryApiError'
  }
}

async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as { detail?: string }
    return body.detail || fallback
  } catch { return fallback }
}

export const industryApi = {
  async getIndustries(): Promise<Industry[]> {
    const response = await fetch(`${apiBaseUrl}/api/industries`)
    if (!response.ok) throw new IndustryApiError(await errorMessage(response, 'Industries could not be loaded. Please try again.'))
    return response.json() as Promise<Industry[]>
  },
  async setFollowed(industryId: string, followed: boolean): Promise<Industry> {
    const response = await fetch(`${apiBaseUrl}/api/industries/${encodeURIComponent(industryId)}/follow`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ followed }),
    })
    if (!response.ok) throw new IndustryApiError(await errorMessage(response, 'Industry follow state could not be saved. Please try again.'))
    return response.json() as Promise<Industry>
  },
}
