import { afterEach, describe, expect, it, vi } from 'vitest'
import { replaceLots } from './lotsApi'

describe('replaceLots', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('replaces active lots including purchase dates through the HTTP API', async () => {
    const asset = { id: 'sap', lots: [{ id: 'lot-1', quantity: '1.25', purchasePrice: '100.10', purchaseDate: '2026-10-20' }] }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(asset), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(replaceLots('sap', asset.lots)).resolves.toEqual(asset)
    expect(fetchMock).toHaveBeenCalledWith('/api/assets/sap/lots', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ lots: asset.lots }) }))
  })

  it('surfaces the server error so the editor can preserve input', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Purchase date cannot be in the future.' }), { status: 422 })))
    await expect(replaceLots('sap', [])).rejects.toThrow('Purchase date cannot be in the future.')
  })
})
