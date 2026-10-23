import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { dashboardApi } from './api/dashboardApi'
import { assetSearchApi } from './api/assetSearchApi'
import { assetCreateApi } from './api/assetCreateApi'
import { industryApi } from './api/industryApi'
import { assetRemoveApi } from './api/assetRemoveApi'
import { replaceLots } from './api/lotsApi'
import { updateAsset } from './api/assetUpdateApi'
import { timelineApi } from './api/timelineApi'
import type { Dashboard, TimelineDay } from './types'

vi.mock('./api/dashboardApi', () => ({
  dashboardApi: { getDashboard: vi.fn() },
}))

vi.mock('./api/assetSearchApi', () => ({
  assetSearchApi: { searchAssets: vi.fn() },
}))

vi.mock('./api/assetCreateApi', () => ({
  assetCreateApi: { createAsset: vi.fn() },
}))

vi.mock('./api/industryApi', () => ({
  industryApi: { getIndustries: vi.fn(), setFollowed: vi.fn() },
}))

vi.mock('./api/assetRemoveApi', () => ({
  assetRemoveApi: { removeAsset: vi.fn() },
}))
vi.mock('./api/lotsApi', () => ({ replaceLots: vi.fn() }))
vi.mock('./api/assetUpdateApi', () => ({ updateAsset: vi.fn() }))
vi.mock('./api/timelineApi', () => ({ timelineApi: { getDay: vi.fn() } }))

const getDashboard = vi.mocked(dashboardApi.getDashboard)
const searchAssets = vi.mocked(assetSearchApi.searchAssets)
const createAsset = vi.mocked(assetCreateApi.createAsset)
const getIndustries = vi.mocked(industryApi.getIndustries)
const setIndustryFollowed = vi.mocked(industryApi.setFollowed)
const removeAsset = vi.mocked(assetRemoveApi.removeAsset)
const saveLots = vi.mocked(replaceLots)
const saveStatus = vi.mocked(updateAsset)
const getTimelineDay = vi.mocked(timelineApi.getDay)

const populatedDashboard: Dashboard = {
  assets: [{ id: 'sap', name: 'SAP SE', ticker: 'SAP', exchange: 'XETRA', type: 'Stock', status: 'Owned', price: 210.35, currency: 'EUR', changePercent: -2.3, asOf: '2026-10-20T09:45:00Z', lots: [{ id: 'sap-1', quantity: '5', purchasePrice: '130.00' }, { id: 'sap-2', quantity: '3', purchasePrice: '150.00' }], industries: ['Enterprise software'] }],
  articles: [{ id: 'asset-news', headline: 'SAP update', source: 'Market Wire', publishedAt: '2026-10-20T09:00:00Z', relevance: 'Direct asset news', assets: ['SAP'], industries: [], snippet: 'Stored article.', url: 'https://example.test/sap' }],
  summaries: [{ id: 'summary-1', assetId: 'sap', summary: 'Possible context; verify the linked report.', articleIds: ['asset-news'] }],
  lastRefreshedAt: '2026-10-20T09:45:00Z',
}

const localDateString = (daysAgo: number) => {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
const localDateLabel = (isoDate: string) => new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(`${isoDate}T12:00:00`))

describe('dashboard', () => {
  beforeEach(() => { vi.resetAllMocks(); setIndustryFollowed.mockResolvedValue({ id: 'industry', name: 'Industry', followed: false }); searchAssets.mockResolvedValue([]); getIndustries.mockResolvedValue([]); removeAsset.mockResolvedValue(); saveLots.mockResolvedValue(populatedDashboard.assets[0]); saveStatus.mockResolvedValue(populatedDashboard.assets[0]); createAsset.mockResolvedValue({ id: 'asml-id', name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Interested', price: null, currency: null, changePercent: null, asOf: null, lots: [], industries: ['Semiconductors'] }) })

  it('renders AI context with movement, persisted source links and the exact disclaimer', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    render(<App />)
    const label = await screen.findByText('AI-generated context')
    const card = label.closest('article')!
    expect(within(card).getByText('Down -2.30%')).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: 'Market Wire ↗' })).toHaveAttribute('href', 'https://example.test/sap')
    expect(screen.getByText('AI-generated market context may be incomplete or incorrect. Verify important conclusions using the linked sources.')).toBeInTheDocument()
  })

  it('keeps the dashboard usable with no stored AI summary', async () => {
    getDashboard.mockResolvedValue({ ...populatedDashboard, summaries: [] })
    render(<App />)
    expect(await screen.findByText('No AI context is stored yet.')).toBeInTheDocument()
    expect(screen.queryByText('AI-generated context')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Refresh data/ })).toBeEnabled()
  })

  it('loads the selected historical date through the timeline API and exposes retryable errors', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    let finishInitialLoad!: (day: TimelineDay) => void
    getTimelineDay.mockImplementationOnce((date) => new Promise<TimelineDay>((resolve) => { finishInitialLoad = (day) => resolve({ ...day, date }) }))
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Timeline' }))
    await waitFor(() => expect(getTimelineDay).toHaveBeenCalled())
    const firstDay = localDateString(1)
    expect(screen.getByText(new RegExp(`Loading ${localDateLabel(firstDay)}`))).toBeInTheDocument()
    expect(getTimelineDay).toHaveBeenLastCalledWith(firstDay)
    const dateButtons = screen.getAllByRole('button', { name: /Load/ })
    expect(dateButtons).toHaveLength(30)
    expect(dateButtons[0]).toHaveAccessibleName(`Load ${localDateLabel(firstDay)}`)
    expect(dateButtons[29]).toHaveAccessibleName(`Load ${localDateLabel(localDateString(30))}`)
    finishInitialLoad({ date: firstDay, source: 'newly-loaded', assets: [{ ...populatedDashboard.assets[0], price: 201.25, changePercent: -1.2 }], articles: [], summaries: [] })
    expect(await screen.findByText('Newly retrieved')).toBeInTheDocument()
    expect(screen.getByText('201.25 EUR')).toBeInTheDocument()

    const secondDay = localDateString(2)
    getTimelineDay.mockImplementationOnce(async (date) => ({ date, source: 'archive', assets: [{ ...populatedDashboard.assets[0], price: 200.5 }], articles: [], summaries: [] }))
    fireEvent.click(screen.getByRole('button', { name: `Load ${localDateLabel(secondDay)}` }))
    await waitFor(() => expect(getTimelineDay).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Loaded from archive')).toBeInTheDocument()
    expect(screen.getByText('200.5 EUR')).toBeInTheDocument()

    const thirdDay = localDateString(3)
    getTimelineDay.mockRejectedValueOnce(new Error('Historical market data is currently unavailable.'))
    fireEvent.click(screen.getByRole('button', { name: `Load ${localDateLabel(thirdDay)}` }))
    expect(await screen.findByRole('alert')).toHaveTextContent(`Could not load ${localDateLabel(thirdDay)}: Historical market data is currently unavailable.`)
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: localDateLabel(secondDay) })).toBeInTheDocument()
    expect(screen.getByText('200.5 EUR')).toBeInTheDocument()
    getTimelineDay.mockImplementationOnce(async (date) => ({ date, source: 'newly-loaded', assets: [{ ...populatedDashboard.assets[0], price: 199.5 }], articles: [], summaries: [] }))
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('199.5 EUR')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: localDateLabel(thirdDay) })).toBeInTheDocument()

    const fourthDay = localDateString(4)
    getTimelineDay.mockImplementationOnce(async (date) => ({ date, source: 'newly-loaded', marketClosed: true, assets: [], articles: [], summaries: [] }))
    fireEvent.click(screen.getByRole('button', { name: `Load ${localDateLabel(fourthDay)}` }))
    await waitFor(() => expect(getTimelineDay).toHaveBeenCalledTimes(5))
    expect(await screen.findByText('No market-day data')).toBeInTheDocument()
  }, 10_000)

  it('separates followed and available industries, and moves an industry after a successful save', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    getIndustries.mockResolvedValue([{ id: 'semi', name: 'Semiconductors', followed: true }, { id: 'energy', name: 'Renewable energy', followed: false }])
    setIndustryFollowed.mockResolvedValue({ id: 'energy', name: 'Renewable energy', followed: true })

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: /Industries 1/ }))
    expect(await screen.findByText('Semiconductors')).toBeInTheDocument()
    expect(screen.getByText('Renewable energy')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Follow' }))

    await waitFor(() => expect(setIndustryFollowed).toHaveBeenCalledWith('energy', true))
    expect(await screen.findAllByRole('button', { name: 'Unfollow' })).toHaveLength(2)
  })

  it('shows an actionable error when industries cannot be loaded', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    getIndustries.mockRejectedValue(new Error('offline'))

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: /Industries 0/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Industries could not be loaded')
    expect(screen.getByText('No new industry suggestions from your watchlist.')).toBeInTheDocument()
  })

  it('explains the empty suggestion state', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    getIndustries.mockResolvedValue([{ id: 'semi', name: 'Semiconductors', followed: true }])

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: /Industries 1/ }))
    expect(await screen.findByText('No new industry suggestions from your watchlist.')).toBeInTheDocument()
  })

  it('keeps displayed industries usable and shows an error when a follow save fails', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    getIndustries.mockResolvedValue([{ id: 'semi', name: 'Semiconductors', followed: true }])
    setIndustryFollowed.mockRejectedValue(new Error('offline'))

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: /Industries 1/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Unfollow' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Industry follow state could not be saved')
    expect(screen.getByText('Semiconductors')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Unfollow' })).toBeInTheDocument()
  })

  it('restores suggestion metadata when an unfollow response omits derived fields', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    getIndustries.mockResolvedValue([{ id: 'semi', name: 'Semiconductors', followed: true, assets: ['ASML'] }])
    setIndustryFollowed.mockResolvedValue({ id: 'semi', name: 'Semiconductors', followed: false })

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: /Industries 1/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Unfollow' }))
    expect(await screen.findByRole('button', { name: 'Follow' })).toBeInTheDocument()
    expect(screen.getByText('From ASML')).toBeInTheDocument()
  })

  it('separates watchlist suggestions, shows supporting assets, and removes one after following', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    getIndustries.mockResolvedValue([{ id: 'semi', name: 'Semiconductors', followed: false, suggested: true, assets: ['ASML', 'SMH'] }, { id: 'energy', name: 'Renewable energy', followed: false }])
    setIndustryFollowed.mockResolvedValue({ id: 'semi', name: 'Semiconductors', followed: true })

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: /Industries 0/ }))
    expect(await screen.findByText('SUGGESTED FROM WATCHLIST')).toBeInTheDocument()
    const suggestedRow = screen.getByText('From ASML, SMH').closest('.industry-row')
    expect(suggestedRow).not.toBeNull()
    fireEvent.click(within(suggestedRow as HTMLElement).getByRole('button', { name: 'Follow' }))
    await waitFor(() => expect(setIndustryFollowed).toHaveBeenCalledWith('semi', true))
    expect(await screen.findByRole('button', { name: 'Unfollow' })).toBeInTheDocument()
    expect(screen.queryByText('From ASML, SMH')).not.toBeInTheDocument()
  })

  it('renders persisted asset, article, and owned-lot details returned by the dashboard API', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)

    render(<App />)

    expect(await screen.findByText('8 active shares')).toBeInTheDocument()
    expect(screen.getAllByText('SAP SE')).toHaveLength(2)
    expect(screen.getByText('8 active shares')).toBeInTheDocument()
    expect(screen.getByText('Avg. €137.50')).toBeInTheDocument()
    expect(screen.getByText('Direct asset news')).toBeInTheDocument()
    expect(screen.getByText('Possible context; verify the linked report.')).toBeInTheDocument()
    expect(getDashboard).toHaveBeenCalledTimes(1)
  })

  it('keeps stored direct news visible and labels it stale when refresh news is unavailable', async () => {
    getDashboard.mockResolvedValue({ ...populatedDashboard, newsStatus: 'stale', articles: [{ ...populatedDashboard.articles[0], snippet: null }] })

    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent('News could not be fully refreshed')
    expect(screen.getByText('SAP update')).toBeInTheDocument()
    expect(screen.queryByText('Stored article.')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /SAP update/i })).toHaveAttribute('href', 'https://example.test/sap')
  })

  it('shows industry news in its own feed with matching industry labels and a useful empty state', async () => {
    const industryArticle = { id: 'industry-1', headline: 'Semiconductor demand outlook', source: 'Market Wire', publishedAt: '2026-10-20T09:00:00Z', relevance: 'Industry news' as const, assets: [], industries: ['Semiconductors', 'Enterprise software'], snippet: 'Stored sector report.', url: 'https://example.test/industry' }
    getDashboard.mockResolvedValue({ ...populatedDashboard, articles: [...populatedDashboard.articles, industryArticle] })

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Industry news' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Semiconductor demand outlook/i })).toHaveAttribute('href', industryArticle.url)
    expect(screen.getByText('Semiconductors')).toBeInTheDocument()
    expect(screen.getByText('Enterprise software')).toBeInTheDocument()

  })

  it('explains when no followed-industry articles are stored', async () => {
    getDashboard.mockResolvedValue({ ...populatedDashboard, articles: [] })
    render(<App />)
    expect(await screen.findByText('No relevant industry news is stored for your followed industries yet.')).toBeInTheDocument()
  })

  it('renders stored market context with its source link and a clear empty state', async () => {
    const marketArticle = { id: 'market-1', headline: 'Central bank holds interest rates steady', source: 'Market Wire', publishedAt: '2026-10-20T09:00:00Z', relevance: 'Market context' as const, assets: [], industries: [], snippet: 'The decision leaves policy unchanged.', url: 'https://example.test/market' }
    getDashboard.mockResolvedValueOnce({ ...populatedDashboard, articles: [marketArticle] })
    const { unmount } = render(<App />)

    expect(await screen.findByRole('heading', { name: 'Market context' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Central bank holds interest rates steady/i })).toHaveAttribute('href', marketArticle.url)
    const marketLink = screen.getByRole('link', { name: /Central bank holds interest rates steady/i })
    expect(marketLink).toHaveTextContent('Market Wire')
    expect(marketLink).toHaveTextContent('2026-10-20T09:00:00Z')
    unmount()

    getDashboard.mockResolvedValueOnce({ ...populatedDashboard, articles: [] })
    render(<App />)
    expect(await screen.findByText('No broader market context is stored yet.')).toBeInTheDocument()
  })

  it('renders a first-use state when the stored dashboard has no assets', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })

    render(<App />)

    expect(await screen.findByText('Start your MarketLens')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add asset/i })).toBeInTheDocument()
    expect(screen.queryByText('0 active shares')).not.toBeInTheDocument()
  })

  it('shows an initial error without fabricated data and retries the dashboard read', async () => {
    getDashboard.mockRejectedValueOnce(new Error('network unavailable')).mockResolvedValueOnce(populatedDashboard)

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('MarketLens could not load stored data')
    expect(screen.queryByText('8 active shares')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByText('8 active shares')).toBeInTheDocument())
    expect(getDashboard).toHaveBeenCalledTimes(2)
  })

  it('searches, selects a catalogue result, and shows a no-match state without changing the watchlist', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    searchAssets.mockImplementation(async (query) => query === 'ASML' ? [{ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock' }] : [])

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: 'ASML' } })
    expect(await screen.findByText('ASML Holding')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /ASML Holding/i }))
    expect(screen.getByText('Selected')).toBeInTheDocument()
    expect(screen.getByText('ASML · Euronext Amsterdam · Stock')).toBeInTheDocument()
    expect(searchAssets).toHaveBeenCalledWith('ASML')

    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: 'unknown' } })
    expect(await screen.findByText('No matching assets found.')).toBeInTheDocument()
  })

  it('shows a catalogue search error and does not select an asset', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    searchAssets.mockRejectedValue(new Error('offline'))

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: 'ASML' } })

    expect(await screen.findByRole('alert')).toHaveTextContent('The asset catalogue could not be searched')
    expect(screen.queryByText('Selected')).not.toBeInTheDocument()
  })

  it('discards a stale catalogue response after a newer query completes', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    let resolveFirstSearch: (results: { name: string; ticker: string; exchange: string; type: 'Stock' }[]) => void
    const firstSearch = new Promise<{ name: string; ticker: string; exchange: string; type: 'Stock' }[]>((resolve) => { resolveFirstSearch = resolve })
    searchAssets.mockImplementationOnce(() => firstSearch).mockResolvedValueOnce([
      { name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock' },
    ])

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    const input = screen.getByPlaceholderText('Search by name or ticker')
    fireEvent.change(input, { target: { value: 'A' } })
    fireEvent.change(input, { target: { value: 'ASML' } })

    expect(await screen.findByText('ASML Holding')).toBeInTheDocument()
    resolveFirstSearch!([{ name: 'Apple Inc.', ticker: 'AAPL', exchange: 'NASDAQ', type: 'Stock' }])
    await waitFor(() => expect(screen.queryByText('Apple Inc.')).not.toBeInTheDocument())
    expect(screen.getByText('ASML Holding')).toBeInTheDocument()
  })

  it('does not request or retain a selection for a whitespace-only query', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: '   ' } })

    await waitFor(() => expect(searchAssets).not.toHaveBeenCalled())
    expect(screen.queryByText('Selected')).not.toBeInTheDocument()
  })

  it('adds a selected catalogue asset, then reloads the dashboard with the saved status', async () => {
    getDashboard.mockResolvedValueOnce({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' }).mockResolvedValueOnce({
      assets: [{ id: 'asml-id', name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Owned', price: null, currency: null, changePercent: null, asOf: null, lots: [], industries: ['Semiconductors'] }], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet',
    })
    searchAssets.mockResolvedValue([{ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock' }])

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: 'ASML' } })
    fireEvent.click(await screen.findByRole('button', { name: /ASML Holding/i }))
    fireEvent.click(screen.getByLabelText('Owned'))
    fireEvent.click(screen.getByRole('button', { name: 'Add to watchlist' }))

    await waitFor(() => expect(createAsset).toHaveBeenCalledWith({ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Owned' }))
    expect(await screen.findByText('Price not refreshed')).toBeInTheDocument()
    expect(screen.getByText('Owned')).toBeInTheDocument()
    expect(getIndustries).toHaveBeenCalledTimes(2)
  })

  it('forces an Index selection to Interested and hides the Owned choice', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    searchAssets.mockResolvedValue([{ name: 'S&P 500', ticker: 'SPX', exchange: 'S&P Dow Jones Indices', type: 'Index' }])

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: 'SPX' } })
    fireEvent.click(await screen.findByRole('button', { name: /S&P 500/i }))

    expect(screen.queryByLabelText('Owned')).not.toBeInTheDocument()
    expect(screen.getByText('Indices are followed for context and cannot be marked as owned.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Add to watchlist' }))
    await waitFor(() => expect(createAsset).toHaveBeenCalledWith({ name: 'S&P 500', ticker: 'SPX', exchange: 'S&P Dow Jones Indices', type: 'Index', status: 'Interested' }))
  })

  it('shows a create error while retaining the selected asset and status', async () => {
    getDashboard.mockResolvedValue({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    searchAssets.mockResolvedValue([{ name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock' }])
    createAsset.mockRejectedValue(new Error('This asset is already in your watchlist.'))

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /add asset/i }))
    fireEvent.change(screen.getByPlaceholderText('Search by name or ticker'), { target: { value: 'ASML' } })
    fireEvent.click(await screen.findByRole('button', { name: /ASML Holding/i }))
    fireEvent.click(screen.getByLabelText('Owned'))
    fireEvent.click(screen.getByRole('button', { name: 'Add to watchlist' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('This asset is already in your watchlist.')
    expect(screen.getByText('Selected')).toBeInTheDocument()
    expect(screen.getByLabelText('Owned')).toBeChecked()
  })

  it('saves edited lots once, closes the editor, and shows refreshed figures on the dashboard', async () => {
    const updated = { ...populatedDashboard, assets: [{ ...populatedDashboard.assets[0], lots: [{ id: 'sap-1', quantity: '10', purchasePrice: '100', purchaseDate: '2026-05-01' }] }] }
    getDashboard.mockResolvedValueOnce(populatedDashboard).mockResolvedValueOnce(updated)
    let resolveSave: (asset: typeof populatedDashboard.assets[number]) => void = () => {}
    saveLots.mockReturnValueOnce(new Promise<typeof populatedDashboard.assets[number]>((resolve) => { resolveSave = resolve }))
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.click(screen.getByRole('button', { name: /add lot/i }))
    fireEvent.change(screen.getByLabelText('Lot 3 quantity'), { target: { value: '2.5' } })
    fireEvent.change(screen.getByLabelText('Lot 3 price'), { target: { value: '99.10' } })
    fireEvent.change(screen.getByLabelText('Lot 3 purchase date'), { target: { value: '2026-05-01' } })
    const saveButton = screen.getByRole('button', { name: 'Save lots' })
    const lastDateField = screen.getByLabelText('Lot 3 purchase date')
    expect(lastDateField.compareDocumentPosition(saveButton) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0)
    fireEvent.click(saveButton)
    fireEvent.click(saveButton)
    expect(saveLots).toHaveBeenCalledTimes(1)
    expect(saveLots).toHaveBeenCalledWith('sap', expect.arrayContaining([expect.objectContaining({ quantity: '2.5', purchasePrice: '99.10', purchaseDate: '2026-05-01' })]))
    resolveSave(updated.assets[0])
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Save lots' })).not.toBeInTheDocument())
    expect(await screen.findByText('10 active shares')).toBeInTheDocument()
    expect(screen.getByText('Avg. €100.00')).toBeInTheDocument()
  })

  it('returns to the dashboard with updated figures after editing from the Watchlist table', async () => {
    const updated = { ...populatedDashboard, assets: [{ ...populatedDashboard.assets[0], lots: [{ id: 'sap-1', quantity: '10', purchasePrice: '100', purchaseDate: '2026-05-01' }] }] }
    getDashboard.mockResolvedValueOnce(populatedDashboard).mockResolvedValueOnce(updated)
    getIndustries.mockResolvedValue([])
    saveLots.mockResolvedValue(updated.assets[0])
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Watchlist' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Manage →' }))
    fireEvent.change(screen.getByLabelText('Lot 1 quantity'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Lot 1 price'), { target: { value: '100' } })
    fireEvent.change(screen.getByLabelText('Lot 1 purchase date'), { target: { value: '2026-05-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save lots' }))
    expect(await screen.findByText('10 active shares')).toBeInTheDocument()
    expect(screen.getByText('Avg. €100.00')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save lots' })).not.toBeInTheDocument()
  })

  it('removes an individual lot and saves only the remaining lots', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove lot 1' }))
    expect(screen.queryByLabelText('Lot 2 quantity')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Lot 1 quantity')).toHaveValue('3')
    expect(screen.getByLabelText('Lot 1 price')).toHaveValue('150.00')
    fireEvent.click(screen.getByRole('button', { name: 'Save lots' }))
    await waitFor(() => expect(saveLots).toHaveBeenCalledWith('sap', [{ id: 'sap-2', quantity: '3', purchasePrice: '150.00' }]))
  })

  it('shows actionable validation feedback for an invalid lot without submitting it', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.change(screen.getByLabelText('Lot 1 quantity'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save lots' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a positive quantity and purchase price')
    expect(screen.getByLabelText('Lot 1 quantity')).toHaveValue('')
    expect(saveLots).not.toHaveBeenCalled()
  })

  it('keeps edited lot input and shows an actionable save error', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    saveLots.mockRejectedValue(new Error('Purchase date cannot be in the future.'))
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.change(screen.getByLabelText('Lot 1 quantity'), { target: { value: '7.125' } })
    fireEvent.change(screen.getByLabelText('Lot 1 purchase date'), { target: { value: '2026-06-01' } })
    const saveButton = screen.getByRole('button', { name: 'Save lots' })
    expect(screen.getByLabelText('Lot 1 purchase date').compareDocumentPosition(saveButton) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0)
    fireEvent.click(saveButton)
    expect(await screen.findByRole('alert')).toHaveTextContent('Purchase date cannot be in the future.')
    expect(screen.getByLabelText('Lot 1 quantity')).toHaveValue('7.125')
    expect(screen.getByLabelText('Lot 1 purchase date')).toHaveValue('2026-06-01')
  })

  it('changes an interested asset to owned with initial lots in one request', async () => {
    const interested = { ...populatedDashboard.assets[0], status: 'Interested' as const, lots: [] }
    const updated = { ...populatedDashboard, assets: [{ ...interested, status: 'Owned' as const, lots: [{ id: 'lot-1', quantity: '2', purchasePrice: '100', purchaseDate: '2026-06-01' }] }] }
    getDashboard.mockResolvedValueOnce({ ...populatedDashboard, assets: [interested] }).mockResolvedValueOnce(updated)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage asset/i }))
    fireEvent.click(screen.getByLabelText('Owned'))
    fireEvent.click(screen.getByRole('button', { name: /add lot/i }))
    fireEvent.change(screen.getByLabelText('Lot 1 quantity'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Lot 1 price'), { target: { value: '100' } })
    fireEvent.change(screen.getByLabelText('Lot 1 purchase date'), { target: { value: '2026-06-01' } })
    const saveButton = screen.getByRole('button', { name: 'Save ownership status' })
    expect(screen.getByLabelText('Lot 1 purchase date').compareDocumentPosition(saveButton) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0)
    fireEvent.click(saveButton)
    await waitFor(() => expect(saveStatus).toHaveBeenCalledWith('sap', { status: 'Owned', lots: [expect.objectContaining({ quantity: '2', purchasePrice: '100', purchaseDate: '2026-06-01' })] }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Save ownership status' })).not.toBeInTheDocument())
    expect(await screen.findByText('2 active shares')).toBeInTheDocument()
    expect(screen.getByText('Avg. €100.00')).toBeInTheDocument()
  })

  it('shows actionable validation feedback for an empty initial Owned lot', async () => {
    getDashboard.mockResolvedValue({ ...populatedDashboard, assets: [{ ...populatedDashboard.assets[0], status: 'Interested', lots: [] }] })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage asset/i }))
    fireEvent.click(screen.getByLabelText('Owned'))
    fireEvent.click(screen.getByRole('button', { name: 'Save ownership status' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Add at least one active purchase lot.')
    expect(saveStatus).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Owned')).toBeChecked()
  })

  it('retains the requested status and initial-lot input when changing ownership fails', async () => {
    const interested = { ...populatedDashboard.assets[0], status: 'Interested' as const, lots: [] }
    getDashboard.mockResolvedValue({ ...populatedDashboard, assets: [interested] })
    saveStatus.mockRejectedValue(new Error('At least one active purchase lot is required when changing to Owned.'))
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /manage asset/i }))
    fireEvent.click(screen.getByLabelText('Owned'))
    fireEvent.click(screen.getByRole('button', { name: /add lot/i }))
    fireEvent.change(screen.getByLabelText('Lot 1 quantity'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Lot 1 price'), { target: { value: '100' } })
    fireEvent.change(screen.getByLabelText('Lot 1 purchase date'), { target: { value: '2026-06-01' } })
    const saveButton = screen.getByRole('button', { name: 'Save ownership status' })
    expect(screen.getByLabelText('Lot 1 purchase date').compareDocumentPosition(saveButton) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0)
    fireEvent.click(saveButton)
    expect(await screen.findByRole('alert')).toHaveTextContent('At least one active purchase lot')
    expect(screen.getByLabelText('Owned')).toBeChecked()
    expect(screen.getByLabelText('Lot 1 quantity')).toHaveValue('2')
    expect(screen.getByLabelText('Lot 1 purchase date')).toHaveValue('2026-06-01')
    expect(screen.getByRole('button', { name: 'Save ownership status' })).toBeInTheDocument()
  })

  it('confirms asset removal and leaves the watchlist unchanged when cancelled', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove from watchlist' }))
    expect(screen.getByText('Remove SAP from the watchlist?')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(removeAsset).not.toHaveBeenCalled()
    expect(screen.queryByText('Remove SAP from the watchlist?')).not.toBeInTheDocument()
    expect(screen.getAllByText('SAP SE')).toHaveLength(2)
  })

  it('removes an asset, closes management, and reloads the empty watchlist', async () => {
    getDashboard.mockResolvedValueOnce(populatedDashboard).mockResolvedValueOnce({ assets: [], articles: [], summaries: [], lastRefreshedAt: 'Not refreshed yet' })
    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove from watchlist' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove asset' }))

    await waitFor(() => expect(removeAsset).toHaveBeenCalledWith('sap'))
    expect(await screen.findByText('Your watchlist is empty. Add an asset to start monitoring.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove asset' })).not.toBeInTheDocument()
    expect(getIndustries).toHaveBeenCalledTimes(2)
  })

  it('shows a retryable removal error while keeping the management panel usable', async () => {
    getDashboard.mockResolvedValue(populatedDashboard)
    removeAsset.mockRejectedValue(new Error('The requested asset was not found.'))
    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: /manage lots/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove from watchlist' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove asset' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('The requested asset was not found.')
    expect(screen.getByRole('button', { name: 'Remove asset' })).toBeEnabled()
    expect(screen.getAllByText('SAP SE')).toHaveLength(2)
  })
})
