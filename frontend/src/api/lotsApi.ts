import type { Asset, Lot } from '../types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export async function replaceLots(assetId: string, lots: Lot[]): Promise<Asset> {
  const response = await fetch(`${apiBaseUrl}/api/assets/${assetId}/lots`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lots }),
  })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? 'Unable to save purchase lots.')
  return response.json() as Promise<Asset>
}
