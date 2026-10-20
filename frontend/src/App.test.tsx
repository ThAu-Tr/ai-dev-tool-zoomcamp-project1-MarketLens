import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { dashboardApi } from './api/dashboardApi'
import type { Dashboard } from './types'

vi.mock('./api/dashboardApi', () => ({
  dashboardApi: { getDashboard: vi.fn() },
}))

const getDashboard = vi.mocked(dashboardApi.getDashboard)

const populatedDashboard: Dashboard = {
  assets: [{ id: 'sap', name: 'SAP SE', ticker: 'SAP', exchange: 'XETRA', type: 'Stock', status: 'Owned', price: 210.35, currency: 'EUR', changePercent: -2.3, asOf: '2026-10-20T09:45:00Z', lots: [{ id: 'sap-1', quantity: '5', purchasePrice: '130.00' }, { id: 'sap-2', quantity: '3', purchasePrice: '150.00' }], industries: ['Enterprise software'] }],
  articles: [{ id: 'asset-news', headline: 'SAP update', source: 'Market Wire', publishedAt: '2026-10-20T09:00:00Z', relevance: 'Direct asset news', assets: ['SAP'], industries: [], snippet: 'Stored article.', url: 'https://example.test/sap' }],
  summaries: [{ id: 'summary-1', assetId: 'sap', summary: 'Possible context; verify the linked report.', articleIds: ['asset-news'] }],
  lastRefreshedAt: '2026-10-20T09:45:00Z',
}

describe('dashboard', () => {
  beforeEach(() => vi.clearAllMocks())

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
})
