import { afterEach, describe, expect, it, vi } from 'vitest'
import { DashboardApiError, dashboardApi } from './dashboardApi'

describe('dashboardApi', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('reads the dashboard from the documented API path', async () => {
    const payload = { assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(dashboardApi.getDashboard()).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith('/api/dashboard')
  })

  it('surfaces a failed dashboard response as an API error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })))

    await expect(dashboardApi.getDashboard()).rejects.toBeInstanceOf(DashboardApiError)
  })
})
