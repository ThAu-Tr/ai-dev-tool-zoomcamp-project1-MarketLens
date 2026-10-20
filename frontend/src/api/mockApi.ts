import type { Asset, AssetSearchResult, Dashboard, Industry, Lot, TimelineDay } from '../types'

const delay = (ms = 380) => new Promise((resolve) => window.setTimeout(resolve, ms))

let assets: Asset[] = [
  { id: 'sap', name: 'SAP SE', ticker: 'SAP', exchange: 'XETRA', type: 'Stock', status: 'Owned', price: 210.35, currency: 'EUR', changePercent: -2.3, asOf: 'Today, 16:40', lots: [{ id: 'sap-1', quantity: '5', purchasePrice: '130.00' }, { id: 'sap-2', quantity: '3', purchasePrice: '150.00' }], industries: ['Enterprise software', 'AI'] },
  { id: 'smh', name: 'VanEck Semiconductor ETF', ticker: 'SMH', exchange: 'NASDAQ', type: 'ETF', status: 'Interested', price: 346.82, currency: 'USD', changePercent: 1.14, asOf: 'Today, 16:35', lots: [], industries: ['Semiconductors', 'AI'] },
  { id: 'dax', name: 'DAX', ticker: 'DAX', exchange: 'XETRA', type: 'Index', status: 'Interested', price: 22418.25, currency: 'EUR', changePercent: -0.68, asOf: 'Today, 17:30', lots: [], industries: ['European market'] },
]

let industries: Industry[] = [
  { id: 'software', name: 'Enterprise software', followed: true, suggestedBy: ['SAP'] },
  { id: 'semi', name: 'Semiconductors', followed: true, suggestedBy: ['SMH'] },
  { id: 'ai', name: 'AI', followed: false, suggestedBy: ['SAP', 'SMH'] },
  { id: 'energy', name: 'Renewable energy', followed: false, suggestedBy: [] },
  { id: 'banking', name: 'Banking', followed: false, suggestedBy: [] },
]

const articles: Dashboard['articles'] = [
  { id: 'a1', headline: 'European enterprise software outlook turns more cautious', source: 'Financial Review', publishedAt: 'Today, 14:12', relevance: 'Direct asset news', assets: ['SAP'], industries: ['Enterprise software'], snippet: 'Analysts highlighted softer spending signals across large European software buyers.', url: 'https://example.com/enterprise-software' },
  { id: 'a2', headline: 'Chip shares advance as demand expectations improve', source: 'Market Wire', publishedAt: 'Today, 13:05', relevance: 'Industry news', assets: ['SMH'], industries: ['Semiconductors'], snippet: 'The sector moved higher after updated demand commentary from several suppliers.', url: 'https://example.com/chip-demand' },
  { id: 'a3', headline: 'Rate expectations shift after central bank remarks', source: 'World Business', publishedAt: 'Today, 11:20', relevance: 'Market context', assets: ['DAX'], industries: ['European market'], snippet: 'The remarks added uncertainty to the near-term interest-rate outlook.', url: 'https://example.com/rates' },
]

let lastRefreshedAt = 'Today, 17:42'
const archive = new Map<string, TimelineDay>()

const summaries: Dashboard['summaries'] = [{ id: 'c1', assetId: 'sap', summary: 'SAP fell 2.3% today. Possible context includes softer European enterprise-software sentiment and recent guidance concerns. The linked reports may be relevant, but they do not establish a single cause.', articleIds: ['a1'] }]

const assetCatalogue: AssetSearchResult[] = [
  { name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock' },
  { name: 'BMW AG', ticker: 'BMW', exchange: 'XETRA', type: 'Stock' },
  { name: 'iShares Global Clean Energy ETF', ticker: 'ICLN', exchange: 'NASDAQ', type: 'ETF' },
  { name: 'Vanguard S&P 500 ETF', ticker: 'VOO', exchange: 'NYSE Arca', type: 'ETF' },
  { name: 'S&P 500', ticker: 'SPX', exchange: 'S&P Dow Jones Indices', type: 'Index' },
]

const cloneAssets = () => assets.map((asset) => ({ ...asset, lots: asset.lots.map((lot) => ({ ...lot })), industries: [...asset.industries] }))

export const mockApi = {
  async refresh(): Promise<void> {
    await delay(1100)
    lastRefreshedAt = 'Just now'
    assets = assets.map((asset) => asset.id === 'smh' ? { ...asset, price: 347.16, changePercent: 1.24, asOf: 'Just now' } : asset)
  },
  async getAssets(): Promise<Asset[]> { await delay(); return cloneAssets() },
  async searchAssets(query: string): Promise<AssetSearchResult[]> {
    await delay(180)
    const normalized = query.trim().toLowerCase()
    return assetCatalogue.filter((asset) => !normalized || `${asset.name} ${asset.ticker}`.toLowerCase().includes(normalized))
  },
  async addAsset(asset: Omit<Asset, 'id' | 'price' | 'currency' | 'changePercent' | 'asOf'>): Promise<Asset> {
    await delay()
    const created: Asset = { ...asset, id: asset.ticker.toLowerCase() + Date.now(), price: 0, currency: 'USD', changePercent: 0, asOf: 'Not refreshed yet' }
    assets = [...assets, created]
    return { ...created, lots: created.lots.map((lot) => ({ ...lot })) }
  },
  async updateLots(assetId: string, lots: Lot[]): Promise<Asset> {
    await delay()
    assets = assets.map((asset) => asset.id === assetId ? { ...asset, lots } : asset)
    return cloneAssets().find((asset) => asset.id === assetId)!
  },
  async deleteAsset(assetId: string): Promise<void> {
    await delay(280)
    assets = assets.filter((asset) => asset.id !== assetId)
  },
  async getIndustries(): Promise<Industry[]> { await delay(); return industries.map((industry) => ({ ...industry, suggestedBy: [...industry.suggestedBy] })) },
  async toggleIndustry(id: string): Promise<void> { await delay(200); industries = industries.map((industry) => industry.id === id ? { ...industry, followed: !industry.followed } : industry) },
  async getTimeline(date: string): Promise<TimelineDay> {
    await delay(archive.has(date) ? 240 : 900)
    const existing = archive.get(date)
    if (existing) return { ...existing, source: 'archive' }
    const weekday = new Date(`${date}T12:00:00`).getDay()
    const day: TimelineDay = weekday === 0 || weekday === 6
      ? { date, source: 'newly-loaded', marketClosed: true, assets: [], articles: [], summaries: [] }
      : { date, source: 'newly-loaded', assets: cloneAssets().map((asset, index) => ({ ...asset, changePercent: [0.72, -0.41, 0.18][index] ?? 0, asOf: date })), articles: articles.map((article) => ({ ...article, publishedAt: `${date}, 13:20` })), summaries: summaries.map((summary) => ({ ...summary })) }
    archive.set(date, day)
    return day
  },
  isArchived(date: string) { return archive.has(date) },
}
