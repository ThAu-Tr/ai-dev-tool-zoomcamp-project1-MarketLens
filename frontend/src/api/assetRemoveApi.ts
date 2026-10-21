const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export class AssetRemoveApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AssetRemoveApiError'
  }
}

export const assetRemoveApi = {
  async removeAsset(assetId: string): Promise<void> {
    const response = await fetch(`${apiBaseUrl}/api/assets/${assetId}`, { method: 'DELETE' })
    if (response.ok) return
    let message = 'The asset could not be removed. Please try again.'
    try {
      const error = await response.json() as { detail?: string }
      if (error.detail) message = error.detail
    } catch { /* Keep a useful retryable error for non-JSON failures. */ }
    throw new AssetRemoveApiError(message)
  },
}
