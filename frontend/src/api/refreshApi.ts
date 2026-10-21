const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export class RefreshApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'RefreshApiError'
  }
}

export const refreshApi = {
  async refresh(): Promise<{ lastRefreshedAt: string }> {
    const response = await fetch(`${apiBaseUrl}/api/refresh`, { method: 'POST' })
    if (!response.ok) throw new RefreshApiError(`Refresh request failed with status ${response.status}`)
    return response.json() as Promise<{ lastRefreshedAt: string }>
  },
}
