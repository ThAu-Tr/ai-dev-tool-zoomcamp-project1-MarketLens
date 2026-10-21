import type { Asset, AssetUpdateRequest } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export async function updateAsset(assetId: string, request: AssetUpdateRequest): Promise<Asset> {
  const response = await fetch(`${apiBaseUrl}/api/assets/${assetId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request),
  })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? 'Unable to save ownership status.')
  return response.json() as Promise<Asset>
}
