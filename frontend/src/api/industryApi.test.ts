import { afterEach, describe, expect, it, vi } from 'vitest'
import { IndustryApiError, industryApi } from './industryApi'

describe('industryApi', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('gets industries and saves a requested follow state through the documented endpoints', async () => {
    const industry = { id: 'semi', name: 'Semiconductors', followed: true }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([industry]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(industry), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(industryApi.getIndustries()).resolves.toEqual([industry])
    await expect(industryApi.setFollowed('semi', true)).resolves.toEqual(industry)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/industries')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/industries/semi/follow', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ followed: true }) }))
  })

  it('preserves a server save error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'The requested industry was not found.' }), { status: 404 })))
    await expect(industryApi.setFollowed('unknown', false)).rejects.toEqual(expect.objectContaining<Partial<IndustryApiError>>({ message: 'The requested industry was not found.' }))
  })
})
