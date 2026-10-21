import { describe, expect, it, vi } from 'vitest'
import { refreshApi } from './refreshApi'

describe('refreshApi', () => {
  it('posts to the refresh endpoint', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ lastRefreshedAt: '2026-10-21T12:00:00Z' }), { status: 200 })))
    await expect(refreshApi.refresh()).resolves.toEqual({ lastRefreshedAt: '2026-10-21T12:00:00Z' })
    expect(fetch).toHaveBeenCalledWith('/api/refresh', { method: 'POST' })
    vi.unstubAllGlobals()
  })
})
