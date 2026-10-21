import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { dashboardApi } from './api/dashboardApi'
import { assetSearchApi } from './api/assetSearchApi'
import { assetCreateApi } from './api/assetCreateApi'
import { industryApi } from './api/industryApi'
import { assetRemoveApi } from './api/assetRemoveApi'
import type { Dashboard } from './types'

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

const getDashboard = vi.mocked(dashboardApi.getDashboard)
const searchAssets = vi.mocked(assetSearchApi.searchAssets)
const createAsset = vi.mocked(assetCreateApi.createAsset)
const getIndustries = vi.mocked(industryApi.getIndustries)
const setIndustryFollowed = vi.mocked(industryApi.setFollowed)
const removeAsset = vi.mocked(assetRemoveApi.removeAsset)

const populatedDashboard: Dashboard = {
  assets: [{ id: 'sap', name: 'SAP SE', ticker: 'SAP', exchange: 'XETRA', type: 'Stock', status: 'Owned', price: 210.35, currency: 'EUR', changePercent: -2.3, asOf: '2026-10-20T09:45:00Z', lots: [{ id: 'sap-1', quantity: '5', purchasePrice: '130.00' }, { id: 'sap-2', quantity: '3', purchasePrice: '150.00' }], industries: ['Enterprise software'] }],
  articles: [{ id: 'asset-news', headline: 'SAP update', source: 'Market Wire', publishedAt: '2026-10-20T09:00:00Z', relevance: 'Direct asset news', assets: ['SAP'], industries: [], snippet: 'Stored article.', url: 'https://example.test/sap' }],
  summaries: [{ id: 'summary-1', assetId: 'sap', summary: 'Possible context; verify the linked report.', articleIds: ['asset-news'] }],
  lastRefreshedAt: '2026-10-20T09:45:00Z',
}

describe('dashboard', () => {
  beforeEach(() => { vi.clearAllMocks(); searchAssets.mockResolvedValue([]); getIndustries.mockResolvedValue([]); removeAsset.mockResolvedValue(); createAsset.mockResolvedValue({ id: 'asml-id', name: 'ASML Holding', ticker: 'ASML', exchange: 'Euronext Amsterdam', type: 'Stock', status: 'Interested', price: null, currency: null, changePercent: null, asOf: null, lots: [], industries: ['Semiconductors'] }) })

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
