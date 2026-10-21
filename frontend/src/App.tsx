import { useEffect, useMemo, useState } from 'react'
import { dashboardApi } from './api/dashboardApi'
import { refreshApi } from './api/refreshApi'
import { assetSearchApi } from './api/assetSearchApi'
import { assetCreateApi } from './api/assetCreateApi'
import { industryApi } from './api/industryApi'
import { assetRemoveApi } from './api/assetRemoveApi'
import { replaceLots } from './api/lotsApi'
import './asset-create.css'
import { mockApi } from './api/mockApi'
import type { Asset, AssetSearchResult, Dashboard, Industry, Lot, Relevance, TimelineDay } from './types'

type View = 'dashboard' | 'watchlist' | 'timeline'

const money = (value: number, currency: string) => new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value)
const SCALE = 1000000n
const decimalInt = (value: string) => { const [whole, fraction = ''] = value.split('.'); return BigInt(whole || '0') * SCALE + BigInt((fraction + '000000').slice(0, 6)) }
const decimalText = (value: bigint) => { const sign = value < 0n ? '-' : ''; const absolute = value < 0n ? -value : value; const whole = absolute / SCALE; const fraction = (absolute % SCALE).toString().padStart(6, '0').replace(/0+$/, ''); return `${sign}${whole}${fraction ? `.${fraction}` : ''}` }
const decimalSum = (values: string[]) => decimalText(values.reduce((sum, value) => sum + decimalInt(value || '0'), 0n))
const decimalAdd = (left: string, right: string) => decimalText(decimalInt(left || '0') + decimalInt(right || '0'))
const decimalMultiply = (left: string, right: string) => decimalText((decimalInt(left || '0') * decimalInt(right || '0')) / SCALE)
const decimalDivide = (left: string, right: string) => decimalText((decimalInt(left || '0') * SCALE) / decimalInt(right || '1'))
const weightedAverage = (lots: Lot[]) => { const quantity = lots.reduce((sum, lot) => sum + decimalInt(lot.quantity || '0'), 0n); if (quantity === 0n) return '0'; const total = lots.reduce((sum, lot) => sum + decimalInt(lot.quantity || '0') * decimalInt(lot.purchasePrice || '0'), 0n); return decimalText(total / quantity) }
const pct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
const today = new Date()
const iso = (date: Date) => date.toISOString().slice(0, 10)
const dateLabel = (date: string) => new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(`${date}T12:00:00`))

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [industries, setIndustries] = useState<Industry[]>([])
  const [industryError, setIndustryError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const nextDashboard = await dashboardApi.getDashboard()
      setDashboard(nextDashboard)
      setError('')
    } catch { setError('MarketLens could not load stored data. Please try again.') }
    finally { setLoading(false) }
  }

  const loadIndustries = async () => {
    try {
      const nextIndustries = await industryApi.getIndustries()
      setIndustries(nextIndustries)
      setIndustryError('')
    } catch { setIndustryError('Industries could not be loaded. Please try again.') }
  }

  useEffect(() => { void load() }, [])
  useEffect(() => { if (view === 'watchlist') void loadIndustries() }, [view])

  const refresh = async () => {
    setRefreshing(true)
    try { await refreshApi.refresh(); await load() }
    catch { setError('Refresh did not complete. Your previous stored data is still shown.') }
    finally { setRefreshing(false) }
  }

  const navigate = (next: View) => { setView(next); setError('') }
  const onAssetSaved = async () => { setAddOpen(false); setSelectedAsset(null); await load(); if (view === 'watchlist') await loadIndustries() }
  const setIndustryFollowed = async (id: string, followed: boolean) => {
    try {
      const updated = await industryApi.setFollowed(id, followed)
      setIndustries((current) => current.map((industry) => {
        if (industry.id !== id) return industry
        // Follow responses from older API versions contain only the persisted
        // state; retain supporting assets so an unfollow can restore a
        // suggestion without briefly displaying a fabricated empty state.
        const assets = updated.assets?.length ? updated.assets : (industry.assets ?? [])
        return { ...industry, ...updated, suggested: followed ? false : (updated.suggested ?? Boolean(assets.length)), assets }
      }))
      setIndustryError('')
    } catch { setIndustryError('Industry follow state could not be saved. Please try again.') }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => navigate('dashboard')} aria-label="Go to Dashboard">
          <span className="brand-mark">M</span><span>MarketLens</span>
        </button>
        <nav aria-label="Main navigation">
          {(['dashboard', 'watchlist', 'timeline'] as View[]).map((item) => <button key={item} className={view === item ? 'nav-link active' : 'nav-link'} onClick={() => navigate(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}
        </nav>
        <div className="topbar-note"><span className="pulse" /> Personal market context</div>
      </header>

      <main>
        {error && <div className="error-banner" role="alert"><span>!</span>{error}<button onClick={() => void load()}>Retry</button><button onClick={() => setError('')}>Dismiss</button></div>}
        {loading && !dashboard ? <LoadingScreen /> : dashboard && <>
          {view === 'dashboard' && <DashboardView dashboard={dashboard} refreshing={refreshing} onRefresh={refresh} onManage={(asset) => { setSelectedAsset(asset); navigate('watchlist') }} onAdd={() => { setAddOpen(true); navigate('watchlist') }} />}
          {view === 'watchlist' && <WatchlistView assets={dashboard.assets} industries={industries} industryError={industryError} initialAsset={selectedAsset} onSelect={(asset) => setSelectedAsset(asset)} onAdd={() => setAddOpen(true)} onChanged={onAssetSaved} onSetIndustryFollowed={setIndustryFollowed} />}
          {view === 'timeline' && <TimelineView assets={dashboard.assets} />}
        </>}
      </main>

      {addOpen && <AssetModal onClose={() => setAddOpen(false)} onSaved={onAssetSaved} />}
    </div>
  )
}

function LoadingScreen() { return <div className="loading-screen"><span className="loader" /> Loading your market context…</div> }

function DashboardView({ dashboard, refreshing, onRefresh, onManage, onAdd }: { dashboard: Dashboard; refreshing: boolean; onRefresh: () => void; onManage: (asset: Asset) => void; onAdd: () => void }) {
  const groups: { title: string; relevance: Relevance; description: string }[] = [
    { title: 'Direct asset news', relevance: 'Direct asset news', description: 'News that directly concerns your followed assets.' },
    { title: 'Industry news', relevance: 'Industry news', description: 'Developments connected to your followed industries.' },
    { title: 'Broader market context', relevance: 'Market context', description: 'Events that may be relevant to the wider market.' },
  ]
  if (!dashboard.assets.length) return <FirstUseDashboard onAdd={onAdd} />
  return <section className="page dashboard-page">
    <div className="eyebrow">TODAY’S VIEW <span>•</span> {dashboard.lastRefreshedAt}</div>
    <div className="page-heading dashboard-heading">
      <div><h1>Market movements,<br /><em>in context.</em></h1><p>Stored data appears immediately. Refresh retrieves only newer available data.</p></div>
      <button className="button primary" disabled={refreshing} onClick={onRefresh}>{refreshing ? <><span className="loader small" /> Refreshing…</> : <>↻ Refresh data</>}</button>
    </div>

    <section className="asset-section" aria-labelledby="assets-heading">
      <div className="section-head"><div><span className="section-kicker">WATCHLIST</span><h2 id="assets-heading">What moved</h2></div><button className="text-button" onClick={onAdd}>+ Add asset</button></div>
      <div className="asset-grid">
        {dashboard.assets.map((asset) => <AssetCard key={asset.id} asset={asset} onManage={() => onManage(asset)} />)}
      </div>
    </section>

    <section className="context-layout">
      <div className="feed-column">
        <div className="section-head"><div><span className="section-kicker">RELEVANT SIGNALS</span><h2>What happened around it</h2></div></div>
        {dashboard.newsStatus === 'stale' && <p className="empty-copy" role="status">News could not be fully refreshed. Previously stored news is shown.</p>}
        {groups.map((group) => <NewsGroup key={group.relevance} {...group} articles={dashboard.articles.filter((article) => article.relevance === group.relevance)} />)}
      </div>
      <aside className="insight-column">
        <span className="section-kicker">AI-GENERATED CONTEXT</span><h2>Possible connections</h2>
        {dashboard.summaries.length ? dashboard.summaries.map((summary) => {
          const asset = dashboard.assets.find((item) => item.id === summary.assetId)
          const sources = dashboard.articles.filter((article) => summary.articleIds.includes(article.id))
          return <article className="insight-card" key={summary.id}><div className="insight-icon">✦</div><span className="chip violet">AI-generated context</span><h3>{asset?.name}</h3><p>{summary.summary}</p><div className="source-list">{sources.map((source) => <a key={source.id} href={source.url} target="_blank" rel="noreferrer">{source.source} ↗</a>)}</div></article>
        }) : <p className="empty-copy">No AI context is stored yet.</p>}
        <p className="disclaimer">AI-generated market context may be incomplete or incorrect. Verify important conclusions using the linked sources.</p>
      </aside>
    </section>
  </section>
}

function FirstUseDashboard({ onAdd }: { onAdd: () => void }) {
  return <section className="page dashboard-page first-use"><div className="eyebrow">YOUR MARKET CONTEXT</div><h1>Start your MarketLens<br /><em>watchlist.</em></h1><p>Add a stock, ETF, or major index to see market movements in context.</p><button className="button primary" onClick={onAdd}>+ Add asset</button></section>
}

function AssetCard({ asset, onManage }: { asset: Asset; onManage: () => void }) {
  const up = (asset.changePercent ?? 0) >= 0
  const quantity = decimalSum(asset.lots.map((lot) => lot.quantity))
  const average = weightedAverage(asset.lots)
  return <article className="asset-card">
    <div className="asset-top"><div><span className="ticker">{asset.ticker}</span><span className="exchange">{asset.exchange}</span></div><span className={`chip ${asset.status === 'Owned' ? 'owned' : 'interested'}`}>{asset.status}</span></div>
    <h3>{asset.name}</h3><span className="asset-type">{asset.type}</span>
    {asset.price === null || asset.currency === null || asset.changePercent === null || asset.asOf === null || asset.priceStatus === 'unavailable'
      ? <><div className="price-line"><strong>{asset.priceStatus === 'unavailable' ? 'Price unavailable' : 'Price not refreshed'}</strong></div><span className="as-of">{asset.priceStatus === 'unavailable' ? 'The provider did not return this symbol; previous data is retained.' : 'Price data will appear after the next refresh.'}</span></>
      : <><div className="price-line"><strong>{money(asset.price, asset.currency)}</strong><span className={up ? 'positive movement' : 'negative movement'}>{up ? '↑' : '↓'} {pct(asset.changePercent)}</span></div><span className="as-of">{asset.priceStatus === 'stale' ? 'Stale price · ' : ''}As of {asset.asOf}</span></>}
    {asset.status === 'Owned' && <div className="holding-detail"><span>{quantity} active shares</span><span>Avg. {asset.currency ? money(Number(average), asset.currency) : 'Not available'}</span></div>}
    <button className="card-action" onClick={onManage}>Manage {asset.status === 'Owned' ? 'lots' : 'asset'} <span>→</span></button>
  </article>
}

function NewsGroup({ title, description, articles }: { title: string; description: string; articles: Dashboard['articles'] }) {
  return <section className="news-group"><div className="news-title"><h3>{title}</h3><p>{description}</p></div>{articles.length ? <div className="article-stack">{articles.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <p className="empty-copy">No relevant news is stored here yet.</p>}</section>
}

function ArticleCard({ article }: { article: Dashboard['articles'][number] }) {
  return <a className="article-card" href={article.url} target="_blank" rel="noreferrer"><div><div className="article-meta"><span className={`dot ${article.relevance === 'Direct asset news' ? 'blue' : article.relevance === 'Industry news' ? 'amber' : 'violet'}`} />{article.source}<span>·</span>{article.publishedAt}</div><h4>{article.headline}</h4>{article.snippet && <p>{article.snippet}</p>}<div className="article-tags">{[...article.assets, ...article.industries].map((tag) => <span key={tag}>{tag}</span>)}</div></div><span className="external">↗</span></a>
}

function WatchlistView({ assets, industries, industryError, initialAsset, onSelect, onAdd, onChanged, onSetIndustryFollowed }: { assets: Asset[]; industries: Industry[]; industryError: string; initialAsset: Asset | null; onSelect: (asset: Asset) => void; onAdd: () => void; onChanged: () => Promise<void>; onSetIndustryFollowed: (id: string, followed: boolean) => Promise<void> }) {
  const [tab, setTab] = useState<'assets' | 'industries'>('assets')
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<Asset | null>(initialAsset)
  useEffect(() => { if (initialAsset) setEditing(initialAsset) }, [initialAsset])
  const filtered = assets.filter((asset) => `${asset.name} ${asset.ticker}`.toLowerCase().includes(query.toLowerCase()))
  return <section className="page watchlist-page">
    <div className="eyebrow">YOUR MONITORING SETUP</div><div className="page-heading"><div><h1>Build a watchlist<br /><em>that stays meaningful.</em></h1><p>Keep assets and themes in one focused monitoring view.</p></div></div>
    <div className="tabbar"><button className={tab === 'assets' ? 'tab active' : 'tab'} onClick={() => setTab('assets')}>Assets <span>{assets.length}</span></button><button className={tab === 'industries' ? 'tab active' : 'tab'} onClick={() => setTab('industries')}>Industries <span>{industries.filter((item) => item.followed).length}</span></button></div>
    {tab === 'assets' ? <><div className="watchlist-toolbar"><label className="search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search assets or tickers" /></label><button className="button primary" onClick={onAdd}>+ Add asset</button></div>{assets.length ? <div className="table-card"><div className="asset-table header-row"><span>Asset</span><span>Type</span><span>Status</span><span>Price</span><span>Industries</span><span /></div>{filtered.map((asset) => <div className="asset-table" key={asset.id}><div><strong>{asset.name}</strong><small>{asset.ticker} · {asset.exchange}</small></div><span>{asset.type}</span><span className={`chip ${asset.status === 'Owned' ? 'owned' : 'interested'}`}>{asset.status}</span><span>{asset.price === null ? 'Price not refreshed' : money(asset.price, asset.currency ?? 'USD')}</span><div className="mini-tags">{asset.industries.map((industry) => <span key={industry}>{industry}</span>)}</div><button className="text-button" onClick={() => { setEditing(asset); onSelect(asset) }}>Manage →</button></div>)}</div> : <p className="empty-copy">Your watchlist is empty. Add an asset to start monitoring.</p>}</> : <IndustryPanel industries={industries} error={industryError} onSetFollowed={onSetIndustryFollowed} />}
    {editing && <LotsPanel asset={editing} onClose={() => setEditing(null)} onSaved={onChanged} />}
  </section>
}

function IndustryPanel({ industries, error, onSetFollowed }: { industries: Industry[]; error: string; onSetFollowed: (id: string, followed: boolean) => Promise<void> }) {
  const [savingId, setSavingId] = useState<string | null>(null)
  const followed = industries.filter((industry) => industry.followed); const suggestions = industries.filter((industry) => industry.suggested && !industry.followed); const available = industries.filter((industry) => !industry.followed && !industry.suggested)
  const save = async (id: string, nextFollowed: boolean) => { setSavingId(id); await onSetFollowed(id, nextFollowed); setSavingId(null) }
  const rows = (items: Industry[]) => items.map((industry) => <div className="industry-row" key={industry.id}><div><strong>{industry.name}</strong>{industry.assets?.length ? <small>From {industry.assets.join(', ')}</small> : null}</div><button className="button subtle" disabled={savingId === industry.id} onClick={() => void save(industry.id, !industry.followed)}>{savingId === industry.id ? 'Saving…' : industry.followed ? 'Unfollow' : 'Follow'}</button></div>)
  return <>{error && <div className="industry-error" role="alert">{error}</div>}<div className="industry-layout"><section className="industry-card"><span className="section-kicker">FOLLOWED</span><h2>Your industry lens <span className="count">{followed.length}</span></h2>{followed.length ? rows(followed) : <p className="empty-copy">Follow industries to surface relevant context.</p>}</section><section className="industry-card suggestion"><span className="section-kicker">SUGGESTED FROM WATCHLIST</span><h2>Industries to consider</h2>{suggestions.length ? rows(suggestions) : <p className="empty-copy">No new industry suggestions from your watchlist.</p>}</section><section className="industry-card"><span className="section-kicker">AVAILABLE</span><h2>Available industries</h2>{available.length ? rows(available) : <p className="empty-copy">All supported industries are followed.</p>}</section></div></>
}

function LotsPanel({ asset, onClose, onSaved }: { asset: Asset; onClose: () => void; onSaved: () => Promise<void> }) {
  const [lots, setLots] = useState<Lot[]>(asset.lots); const [saving, setSaving] = useState(false); const [confirmingRemoval, setConfirmingRemoval] = useState(false); const [removeError, setRemoveError] = useState(''); const [saveError, setSaveError] = useState('')
  const updateLot = (id: string, field: keyof Lot, value: string | null) => setLots((current) => current.map((lot) => lot.id === id ? { ...lot, [field]: value } : lot))
  const valid = lots.length > 0 && lots.every((lot) => /^\d+(\.\d{1,6})?$/.test(lot.quantity) && /^\d+(\.\d{1,6})?$/.test(lot.purchasePrice) && decimalInt(lot.quantity) > 0n && decimalInt(lot.purchasePrice) > 0n && (!lot.purchaseDate || lot.purchaseDate <= new Date().toISOString().slice(0, 10)))
  const save = async () => { if (!valid) return; setSaving(true); setSaveError(''); try { await replaceLots(asset.id, lots); await onSaved() } catch (error) { const message = error instanceof Error ? error.message : 'Unable to save lots. Your changes are still here.'; setSaveError(message); setRemoveError(message) } finally { setSaving(false) } }
  const quantity = decimalSum(lots.map((lot) => lot.quantity || '0')); const average = weightedAverage(lots)
  const remove = async () => {
    setSaving(true); setRemoveError('')
    try { await assetRemoveApi.removeAsset(asset.id); await onSaved(); onClose() }
    catch (error) { setRemoveError(error instanceof Error ? error.message : 'The asset could not be removed. Please try again.') }
    finally { setSaving(false) }
  }
  if (asset.status !== 'Owned') return <aside className="side-panel"><button className="close-button" onClick={onClose} aria-label="Close asset management">×</button><span className="section-kicker">MANAGE ASSET</span><h2>{asset.name}</h2><p className="muted">{asset.ticker} · {asset.exchange} · {asset.type}</p><p className="panel-note">Only owned assets can have active purchase lots.</p></aside>
  return <aside className="side-panel"><button className="close-button" onClick={onClose} aria-label="Close asset management">×</button><span className="section-kicker">MANAGE ASSET</span><h2>{asset.name}</h2><p className="muted">{asset.ticker} · {asset.exchange} · {asset.type}</p>{asset.type === 'Index' ? <p className="panel-note">Indices are followed for market context and cannot be marked as owned.</p> : <><h3>Active purchase lots</h3><p className="muted">Adjust or remove lots to reflect a partial sale. Sell history is outside this MVP.</p><div className="lots">{lots.map((lot, index) => <div className="lot-row" key={lot.id}><span>Lot {index + 1}</span><label>Qty<input aria-label={`Lot ${index + 1} quantity`} value={lot.quantity} inputMode="decimal" onChange={(event) => updateLot(lot.id, 'quantity', event.target.value)} /></label><label>Price<input aria-label={`Lot ${index + 1} price`} value={lot.purchasePrice} inputMode="decimal" onChange={(event) => updateLot(lot.id, 'purchasePrice', event.target.value)} /></label><label>Date<input aria-label={`Lot ${index + 1} purchase date`} type="date" max={new Date().toISOString().slice(0, 10)} value={lot.purchaseDate ?? ''} onChange={(event) => updateLot(lot.id, 'purchaseDate', event.target.value || null)} /></label><button className="icon-button" onClick={() => setLots((current) => current.filter((item) => item.id !== lot.id))} aria-label={`Remove lot ${index + 1}`}>×</button></div>)}</div><button className="text-button" onClick={() => setLots((current) => [...current, { id: crypto.randomUUID(), quantity: '', purchasePrice: '' }])}>+ Add lot</button><div className="lot-total"><span>Total quantity<strong>{quantity || '—'}</strong></span><span>Weighted average<strong>{quantity && asset.currency ? money(Number(average), asset.currency) : '—'}</strong></span></div><button className="button primary full" disabled={!valid || saving} onClick={save}>{saving ? 'Saving…' : 'Save lots'}</button></>}<div className="remove-zone"><h3>Stop following this asset</h3><p>It will leave your watchlist. Previously stored timeline data remains in your personal archive.</p>{confirmingRemoval ? <div className="remove-confirm"><span>Remove {asset.ticker} from the watchlist?</span><button className="button danger" disabled={saving} onClick={() => void remove()}>{saving ? 'Removing…' : 'Remove asset'}</button><button className="text-button" onClick={() => { setConfirmingRemoval(false); setRemoveError('') }}>Cancel</button></div> : <button className="button danger-outline" onClick={() => { setRemoveError(''); setConfirmingRemoval(true) }}>Remove from watchlist</button>}{removeError && <p className="form-error" role="alert">{removeError}</p>}</div></aside>
}

function AssetModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => Promise<void> }) {
  const [status, setStatus] = useState<'Owned' | 'Interested'>('Interested'); const [query, setQuery] = useState(''); const [results, setResults] = useState<AssetSearchResult[]>([]); const [selected, setSelected] = useState<AssetSearchResult | null>(null); const [searching, setSearching] = useState(false); const [searchError, setSearchError] = useState(''); const [createError, setCreateError] = useState(''); const [saving, setSaving] = useState(false)
  useEffect(() => {
    let active = true
    const normalizedQuery = query.trim()
    setResults([])
    setSearchError('')
    if (!normalizedQuery) { setSearching(false); return () => { active = false } }
    setSearching(true)
    void assetSearchApi.searchAssets(normalizedQuery).then((next) => {
      if (active) { setResults(next); setSearching(false) }
    }).catch(() => {
      if (active) { setSearchError('The asset catalogue could not be searched. Please try again.'); setSearching(false) }
    })
    return () => { active = false }
  }, [query])
  const choose = (asset: AssetSearchResult) => { setSelected(asset); setQuery(asset.name); setStatus('Interested'); setCreateError('') }
  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!selected) return
    setSaving(true); setCreateError('')
    try {
      await assetCreateApi.createAsset({ name: selected.name, ticker: selected.ticker, exchange: selected.exchange, type: selected.type, status: selected.type === 'Index' ? 'Interested' : status })
      await onSaved()
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'The selected asset could not be added. Please try again.')
    } finally { setSaving(false) }
  }
  return <div className="modal-backdrop" role="presentation"><form className="modal" onSubmit={save}><button type="button" className="close-button" onClick={onClose} aria-label="Close add asset form">×</button><span className="section-kicker">WATCHLIST</span><h2>Add an asset</h2><p className="muted">Search the supported asset catalogue and select a valid result.</p><label>Search assets<input value={query} onChange={(event) => { setQuery(event.target.value); setSelected(null); setCreateError('') }} placeholder="Search by name or ticker" autoFocus /></label><div className="search-results" aria-live="polite">{searching ? <span>Searching…</span> : searchError ? <span role="alert">{searchError}</span> : query.trim() && results.length ? results.map((asset) => <button type="button" key={`${asset.ticker}-${asset.exchange}`} className={selected?.ticker === asset.ticker ? 'search-result selected' : 'search-result'} onClick={() => choose(asset)}><strong>{asset.name}</strong><span>{asset.ticker} · {asset.exchange} · {asset.type}</span></button>) : query.trim() ? <span>No matching assets found.</span> : <span>Enter a name or ticker to search the catalogue.</span>}</div>{createError && <p role="alert" className="form-error">{createError}</p>}{selected && <div className="selected-asset"><span>Selected</span><strong>{selected.name}</strong><small>{selected.ticker} · {selected.exchange} · {selected.type}</small></div>}{selected?.type !== 'Index' && <fieldset><legend>Follow status</legend><label className="radio"><input type="radio" checked={status === 'Interested'} onChange={() => setStatus('Interested')} name="status" /> Interested</label><label className="radio"><input type="radio" checked={status === 'Owned'} onChange={() => setStatus('Owned')} name="status" /> Owned</label></fieldset>}{selected?.type === 'Index' && <p className="panel-note">Indices are followed for context and cannot be marked as owned.</p>}<button className="button primary full" disabled={!selected || saving}>{saving ? 'Adding…' : 'Add to watchlist'}</button></form></div>
}

function TimelineView({ assets }: { assets: Asset[] }) {
  const initial = iso(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)); const [selected, setSelected] = useState(initial); const [day, setDay] = useState<TimelineDay | null>(null); const [loading, setLoading] = useState(false)
  useEffect(() => { void loadDay(initial) }, [])
  const dates = useMemo(() => Array.from({ length: 30 }, (_, index) => { const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - index); return iso(date) }), [])
  async function loadDay(date: string) { setSelected(date); setLoading(true); const result = await mockApi.getTimeline(date); setDay(result); setLoading(false) }
  return <section className="page timeline-page"><div className="eyebrow">PERSISTENT PERSONAL ARCHIVE</div><div className="page-heading"><div><h1>See the day<br /><em>as it unfolded.</em></h1><p>Choose a recent date. New days are loaded once and kept in your archive.</p></div></div><div className="timeline-layout"><aside className="calendar-card"><div className="calendar-head"><h2>Last 30 days</h2><span>Stored <i /></span></div><div className="date-grid">{dates.map((date) => <button key={date} className={`${selected === date ? 'selected ' : ''}${mockApi.isArchived(date) ? 'archived' : ''}`} onClick={() => void loadDay(date)} aria-label={`Load ${dateLabel(date)}`}><small>{new Date(`${date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short' })}</small><strong>{new Date(`${date}T12:00:00`).getDate()}</strong></button>)}</div><p className="calendar-note"><i /> Stored archive day &nbsp; · &nbsp; Other dates load on first open</p></aside><section className="day-view"><div className="day-title"><div><span className="section-kicker">SELECTED DAY</span><h2>{dateLabel(selected)}</h2></div>{day && <span className="chip neutral">{day.source === 'archive' ? 'Loaded from archive' : 'Newly retrieved'}</span>}</div>{loading ? <div className="day-loading"><span className="loader" /> Loading and saving this day’s context…</div> : day?.marketClosed ? <div className="closed-state"><span>◷</span><h3>No market-day data</h3><p>This selected date is a weekend. Market data may be unavailable, and no context was retrieved.</p></div> : day && <><div className="timeline-movements">{day.assets.map((asset) => <div key={asset.id}><span>{asset.ticker}</span>{asset.changePercent === null ? <strong>Not refreshed</strong> : <strong className={asset.changePercent >= 0 ? 'positive' : 'negative'}>{pct(asset.changePercent)}</strong>}</div>)}</div><div className="timeline-news"><NewsGroup title="Relevant news" description="Articles available for this trading date." articles={day.articles} /></div><p className="timeline-footnote">Article publication times and exchange trading dates may differ. Linked reports provide possible context, not proof of causality.</p></>}</section></div></section>
}
