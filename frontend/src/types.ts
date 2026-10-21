export type AssetType = 'Stock' | 'ETF' | 'Index'
export type FollowStatus = 'Owned' | 'Interested'
export type Relevance = 'Direct asset news' | 'Industry news' | 'Market context'

export type Lot = { id: string; quantity: string; purchasePrice: string; purchaseDate?: string | null }

export type Asset = {
  id: string
  name: string
  ticker: string
  exchange: string
  type: AssetType
  status: FollowStatus
  price: number | null
  currency: string | null
  changePercent: number | null
  asOf: string | null
  lots: Lot[]
  industries: string[]
  priceStatus?: 'current' | 'stale' | 'unavailable' | 'never'
}

export type AssetSearchResult = Pick<Asset, 'name' | 'ticker' | 'exchange' | 'type'>

export type AssetCreateRequest = Pick<Asset, 'name' | 'ticker' | 'exchange' | 'type' | 'status'>
export type AssetUpdateRequest = { status: FollowStatus; lots?: Lot[] }

export type Article = {
  id: string
  headline: string
  source: string
  publishedAt: string
  relevance: Relevance
  assets: string[]
  industries: string[]
  snippet: string | null
  url: string
}

export type ContextSummary = {
  id: string
  assetId: string
  summary: string
  articleIds: string[]
}

export type Dashboard = {
  assets: Asset[]
  articles: Article[]
  summaries: ContextSummary[]
  lastRefreshedAt: string
  newsStatus?: 'current' | 'stale'
}

export type Industry = { id: string; name: string; followed: boolean; suggested?: boolean; assets?: string[] }

export type TimelineDay = {
  date: string
  source: 'archive' | 'newly-loaded'
  marketClosed?: boolean
  assets: Asset[]
  articles: Article[]
  summaries: ContextSummary[]
}
