import { afterEach, describe, expect, it, vi } from 'vitest'
import { AssetRemoveApiError, assetRemoveApi } from './assetRemoveApi'

describe('assetRemoveApi', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('deletes the selected asset through the HTTP API', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(assetRemoveApi.removeAsset('sap')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('/api/assets/sap', { method: 'DELETE' })
  })

  it('preserves a retryable server error message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'The requested asset was not found.' }), { status: 404 })))
    await expect(assetRemoveApi.removeAsset('missing')).rejects.toEqual(expect.objectContaining<Partial<AssetRemoveApiError>>({ message: 'The requested asset was not found.' }))
  })
})
