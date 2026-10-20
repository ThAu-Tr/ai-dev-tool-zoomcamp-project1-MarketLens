import type { Asset, AssetCreateRequest } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export class AssetCreateApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AssetCreateApiError'
  }
}

export const assetCreateApi = {
  async createAsset(request: AssetCreateRequest): Promise<Asset> {
    const response = await fetch(`${apiBaseUrl}/api/assets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    if (!response.ok) {
      let message = 'The selected asset could not be added. Please try again.'
      try {
        const error = await response.json() as { detail?: string }
        if (error.detail) message = error.detail
      } catch { /* Keep the actionable fallback for non-JSON failures. */ }
      throw new AssetCreateApiError(message)
    }
    return response.json() as Promise<Asset>
  },
}
