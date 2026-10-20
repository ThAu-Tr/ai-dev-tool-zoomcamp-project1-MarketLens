import { afterEach, describe, expect, it, vi } from 'vitest'
import { AssetSearchApiError, assetSearchApi } from './assetSearchApi'

describe('assetSearchApi', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('searches the documented endpoint with an encoded query', async () => {
    const payload = [{ name: 'S&P 500', ticker: 'SPX', exchange: 'S&P Dow Jones Indices', type: 'Index' }]
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(assetSearchApi.searchAssets('S&P')).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith('/api/assets/search?q=S%26P')
  })

  it('surfaces failed catalogue responses as API errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 422 })))
    await expect(assetSearchApi.searchAssets('ASML')).rejects.toBeInstanceOf(AssetSearchApiError)
  })
})
