import type { Dashboard } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export class DashboardApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'DashboardApiError'
  }
}

export const dashboardApi = {
  async getDashboard(): Promise<Dashboard> {
    const response = await fetch(`${apiBaseUrl}/api/dashboard`)
    if (!response.ok) {
      throw new DashboardApiError(`Dashboard request failed with status ${response.status}`)
    }
    return response.json() as Promise<Dashboard>
  },
}
