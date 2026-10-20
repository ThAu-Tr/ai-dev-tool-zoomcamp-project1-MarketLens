import { afterEach, describe, expect, it, vi } from 'vitest'
import { AssetCreateApiError, assetCreateApi } from './assetCreateApi'

describe('assetCreateApi', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('posts only a selected catalogue identity and status', async () => {
    const response = { id: 'asset-id', name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Interested', price: null, currency: null, changePercent: null, asOf: null, lots: [], industries: ['Semiconductors'] }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(assetCreateApi.createAsset({ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Interested' })).resolves.toEqual(response)

    expect(fetchMock).toHaveBeenCalledWith('/api/assets', expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Interested' }) }))
  })

  it('preserves the server validation message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'This asset is already in your watchlist.' }), { status: 422 })))

    await expect(assetCreateApi.createAsset({ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Interested' })).rejects.toEqual(expect.objectContaining<Partial<AssetCreateApiError>>({ message: 'This asset is already in your watchlist.' }))
  })
})
