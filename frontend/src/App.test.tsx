import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { dashboardApi } from './api/dashboardApi'
import { assetSearchApi } from './api/assetSearchApi'
import type { Dashboard } from './types'

vi.mock('./api/dashboardApi', () => ({
  dashboardApi: { getDashboard: vi.fn() },
}))

vi.mock('./api/assetSearchApi', () => ({
  assetSearchApi: { searchAssets: vi.fn() },
}))

const getDashboard = vi.mocked(dashboardApi.getDashboard)
const searchAssets = vi.mocked(assetSearchApi.searchAssets)

const populatedDashboard: Dashboard = {
  assets: [{ id: 'sap', name: 'SAP SE', ticker: 'SAP', exchange: 'XETRA', type: 'Stock', status: 'Owned', price: 210.35, currency: 'EUR', changePercent: -2.3, asOf: '2026-10-20T09:45:00Z', lots: [{ id: 'sap-1', quantity: '5', purchasePrice: '130.00' }, { id: 'sap-2', quantity: '3', purchasePrice: '150.00' }], industries: ['Enterprise software'] }],
  articles: [{ id: 'asset-news', headline: 'SAP update', source: 'Market Wire', publishedAt: '2026-10-20T09:00:00Z', relevance: 'Direct asset news', assets: ['SAP'], industries: [], snippet: 'Stored article.', url: 'https://example.test/sap' }],
  summaries: [{ id: 'summary-1', assetId: 'sap', summary: 'Possible context; verify the linked report.', articleIds: ['asset-news'] }],
  lastRefreshedAt: '2026-10-20T09:45:00Z',
}

describe('dashboard', () => {
  beforeEach(() => { vi.clearAllMocks(); searchAssets.mockResolvedValue([]) })

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
})
