import type { AssetSearchResult } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export class AssetSearchApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AssetSearchApiError'
  }
}

export const assetSearchApi = {
  async searchAssets(query: string): Promise<AssetSearchResult[]> {
    const response = await fetch(`${apiBaseUrl}/api/assets/search?${new URLSearchParams({ q: query })}`)
    if (!response.ok) {
      throw new AssetSearchApiError(`Asset catalogue request failed with status ${response.status}`)
    }
    return response.json() as Promise<AssetSearchResult[]>
  },
}
