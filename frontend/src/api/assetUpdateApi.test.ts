import { describe, expect, it, vi } from 'vitest'
import { updateAsset } from './assetUpdateApi'

describe('updateAsset', () => {
  it('patches ownership and initial lots together', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'a' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await updateAsset('a', { status: 'Owned', lots: [{ id: 'lot-1', quantity: '2', purchasePrice: '10' }] })
    expect(fetchMock).toHaveBeenCalledWith('/api/assets/a', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ status: 'Owned', lots: [{ id: 'lot-1', quantity: '2', purchasePrice: '10' }] }) }))
  })

  it('exposes the server validation message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'At least one active purchase lot is required when changing to Owned.' }), { status: 422 })))
    await expect(updateAsset('a', { status: 'Owned' })).rejects.toThrow('At least one active purchase lot')
  })
})
