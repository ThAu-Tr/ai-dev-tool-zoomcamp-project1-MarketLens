export type AssetType = 'Stock' | 'ETF' | 'Index'
export type FollowStatus = 'Owned' | 'Interested'
export type Relevance = 'Direct asset news' | 'Industry news' | 'Market context'

export type Lot = { id: string; quantity: string; purchasePrice: string }

export type Asset = {
  id: string
  name: string
  ticker: string
  exchange: string
  type: AssetType
  status: FollowStatus
  price: number
  currency: string
  changePercent: number
  asOf: string
  lots: Lot[]
  industries: string[]
}

export type AssetSearchResult = Pick<Asset, 'name' | 'ticker' | 'exchange' | 'type'>

export type Article = {
  id: string
  headline: string
  source: string
  publishedAt: string
  relevance: Relevance
  assets: string[]
  industries: string[]
  snippet: string
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
  lastRefreshedAt: string | null
}

export type Industry = { id: string; name: string; followed: boolean; suggestedBy: string[] }

export type TimelineDay = {
  date: string
  source: 'archive' | 'newly-loaded'
  marketClosed?: boolean
  assets: Asset[]
  articles: Article[]
  summaries: ContextSummary[]
}
