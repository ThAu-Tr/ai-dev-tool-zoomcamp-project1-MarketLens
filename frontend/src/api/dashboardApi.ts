import type { Dashboard } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export function createTraceparent(): string {
  const randomHex = (size: number) => {
    const bytes = crypto.getRandomValues(new Uint8Array(size))
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  }
  return `00-${randomHex(16)}-${randomHex(8)}-01`
}

export class DashboardApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'DashboardApiError'
  }
}

export const dashboardApi = {
  async getDashboard(): Promise<Dashboard> {
    const response = await fetch(`${apiBaseUrl}/api/dashboard`, {
      headers: { traceparent: createTraceparent() },
    })
    if (!response.ok) {
      throw new DashboardApiError(`Dashboard request failed with status ${response.status}`)
    }
    return response.json() as Promise<Dashboard>
  },
}
