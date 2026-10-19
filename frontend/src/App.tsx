import { useEffect, useMemo, useState } from 'react'
import { mockApi } from './api/mockApi'
import type { Asset, AssetSearchResult, Dashboard, Industry, Lot, Relevance, TimelineDay } from './types'

type View = 'dashboard' | 'watchlist' | 'timeline'

const money = (value: number, currency: string) => new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value)
const pct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
const today = new Date()
const iso = (date: Date) => date.toISOString().slice(0, 10)
const dateLabel = (date: string) => new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(`${date}T12:00:00`))

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [industries, setIndustries] = useState<Industry[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const [nextDashboard, nextIndustries] = await Promise.all([mockApi.getDashboard(), mockApi.getIndustries()])
      setDashboard(nextDashboard)
      setIndustries(nextIndustries)
      setError('')
    } catch { setError('MarketLens could not load stored data. Please try again.') }
    finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [])

  const refresh = async () => {
    setRefreshing(true)
    try { await mockApi.refresh(); await load() }
    catch { setError('Refresh did not complete. Your previous stored data is still shown.') }
    finally { setRefreshing(false) }
  }

  const navigate = (next: View) => { setView(next); setError('') }
  const onAssetSaved = async () => { setAddOpen(false); setSelectedAsset(null); await load() }

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
        {error && <div className="error-banner" role="alert"><span>!</span>{error}<button onClick={() => setError('')}>Dismiss</button></div>}
        {loading && !dashboard ? <LoadingScreen /> : dashboard && <>
          {view === 'dashboard' && <DashboardView dashboard={dashboard} refreshing={refreshing} onRefresh={refresh} onManage={(asset) => { setSelectedAsset(asset); navigate('watchlist') }} onAdd={() => { setAddOpen(true); navigate('watchlist') }} />}
          {view === 'watchlist' && <WatchlistView assets={dashboard.assets} industries={industries} initialAsset={selectedAsset} onSelect={(asset) => setSelectedAsset(asset)} onAdd={() => setAddOpen(true)} onChanged={onAssetSaved} />}
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
    { title: 'Industry pulse', relevance: 'Industry news', description: 'Developments connected to your followed industries.' },
    { title: 'Broader market context', relevance: 'Market context', description: 'Events that may be relevant to the wider market.' },
  ]
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
        {groups.map((group) => <NewsGroup key={group.relevance} {...group} articles={dashboard.articles.filter((article) => article.relevance === group.relevance)} />)}
      </div>
      <aside className="insight-column">
        <span className="section-kicker">AI-GENERATED CONTEXT</span><h2>Possible connections</h2>
        {dashboard.summaries.map((summary) => {
          const asset = dashboard.assets.find((item) => item.id === summary.assetId)
          const sources = dashboard.articles.filter((article) => summary.articleIds.includes(article.id))
          return <article className="insight-card" key={summary.id}><div className="insight-icon">✦</div><span className="chip violet">AI-generated context</span><h3>{asset?.name}</h3><p>{summary.summary}</p><div className="source-list">{sources.map((source) => <a key={source.id} href={source.url} target="_blank" rel="noreferrer">{source.source} ↗</a>)}</div></article>
        })}
        <p className="disclaimer">AI-generated market context may be incomplete or incorrect. Verify important conclusions using the linked sources.</p>
      </aside>
    </section>
  </section>
}

function AssetCard({ asset, onManage }: { asset: Asset; onManage: () => void }) {
  const up = asset.changePercent >= 0
  const quantity = asset.lots.reduce((sum, lot) => sum + Number(lot.quantity), 0)
  const average = quantity ? asset.lots.reduce((sum, lot) => sum + Number(lot.quantity) * Number(lot.purchasePrice), 0) / quantity : 0
  return <article className="asset-card">
    <div className="asset-top"><div><span className="ticker">{asset.ticker}</span><span className="exchange">{asset.exchange}</span></div><span className={`chip ${asset.status === 'Owned' ? 'owned' : 'interested'}`}>{asset.status}</span></div>
    <h3>{asset.name}</h3><span className="asset-type">{asset.type}</span>
    <div className="price-line"><strong>{asset.price ? money(asset.price, asset.currency) : '—'}</strong><span className={up ? 'positive movement' : 'negative movement'}>{up ? '↑' : '↓'} {pct(asset.changePercent)}</span></div>
    <span className="as-of">As of {asset.asOf}</span>
    {asset.status === 'Owned' && <div className="holding-detail"><span>{quantity} active shares</span><span>Avg. {money(average, asset.currency)}</span></div>}
    <button className="card-action" onClick={onManage}>Manage {asset.status === 'Owned' ? 'lots' : 'asset'} <span>→</span></button>
  </article>
}

function NewsGroup({ title, description, articles }: { title: string; description: string; articles: Dashboard['articles'] }) {
  return <section className="news-group"><div className="news-title"><h3>{title}</h3><p>{description}</p></div>{articles.length ? <div className="article-stack">{articles.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <p className="empty-copy">No relevant news is stored here yet.</p>}</section>
}

function ArticleCard({ article }: { article: Dashboard['articles'][number] }) {
  return <a className="article-card" href={article.url} target="_blank" rel="noreferrer"><div><div className="article-meta"><span className={`dot ${article.relevance === 'Direct asset news' ? 'blue' : article.relevance === 'Industry news' ? 'amber' : 'violet'}`} />{article.source}<span>·</span>{article.publishedAt}</div><h4>{article.headline}</h4><p>{article.snippet}</p><div className="article-tags">{[...article.assets, ...article.industries].map((tag) => <span key={tag}>{tag}</span>)}</div></div><span className="external">↗</span></a>
}

function WatchlistView({ assets, industries, initialAsset, onSelect, onAdd, onChanged }: { assets: Asset[]; industries: Industry[]; initialAsset: Asset | null; onSelect: (asset: Asset) => void; onAdd: () => void; onChanged: () => Promise<void> }) {
  const [tab, setTab] = useState<'assets' | 'industries'>('assets')
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<Asset | null>(initialAsset)
  useEffect(() => { if (initialAsset) setEditing(initialAsset) }, [initialAsset])
  const filtered = assets.filter((asset) => `${asset.name} ${asset.ticker}`.toLowerCase().includes(query.toLowerCase()))
  const toggleIndustry = async (id: string) => { await mockApi.toggleIndustry(id); await onChanged() }
  return <section className="page watchlist-page">
    <div className="eyebrow">YOUR MONITORING SETUP</div><div className="page-heading"><div><h1>Build a watchlist<br /><em>that stays meaningful.</em></h1><p>Keep assets and themes in one focused monitoring view.</p></div></div>
    <div className="tabbar"><button className={tab === 'assets' ? 'tab active' : 'tab'} onClick={() => setTab('assets')}>Assets <span>{assets.length}</span></button><button className={tab === 'industries' ? 'tab active' : 'tab'} onClick={() => setTab('industries')}>Industries <span>{industries.filter((item) => item.followed).length}</span></button></div>
    {tab === 'assets' ? <><div className="watchlist-toolbar"><label className="search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search assets or tickers" /></label><button className="button primary" onClick={onAdd}>+ Add asset</button></div><div className="table-card"><div className="asset-table header-row"><span>Asset</span><span>Type</span><span>Status</span><span>Industries</span><span /></div>{filtered.map((asset) => <div className="asset-table" key={asset.id}><div><strong>{asset.name}</strong><small>{asset.ticker} · {asset.exchange}</small></div><span>{asset.type}</span><span className={`chip ${asset.status === 'Owned' ? 'owned' : 'interested'}`}>{asset.status}</span><div className="mini-tags">{asset.industries.map((industry) => <span key={industry}>{industry}</span>)}</div><button className="text-button" onClick={() => { setEditing(asset); onSelect(asset) }}>Manage →</button></div>)}</div></> : <IndustryPanel industries={industries} onToggle={toggleIndustry} />}
    {editing && <LotsPanel asset={editing} onClose={() => setEditing(null)} onSaved={onChanged} />}
  </section>
}

function IndustryPanel({ industries, onToggle }: { industries: Industry[]; onToggle: (id: string) => void }) {
  const followed = industries.filter((industry) => industry.followed); const suggestions = industries.filter((industry) => !industry.followed && industry.suggestedBy.length); const manualChoices = industries.filter((industry) => !industry.followed && !industry.suggestedBy.length)
  return <div className="industry-layout"><section className="industry-card"><span className="section-kicker">FOLLOWED</span><h2>Your industry lens</h2>{followed.length ? followed.map((industry) => <div className="industry-row" key={industry.id}><div><strong>{industry.name}</strong><small>{industry.suggestedBy.length ? `Linked to ${industry.suggestedBy.join(', ')}` : 'Manually followed'}</small></div><button className="icon-button" aria-label={`Unfollow ${industry.name}`} onClick={() => onToggle(industry.id)}>×</button></div>) : <p className="empty-copy">Follow industries to surface relevant context.</p>}</section><section className="industry-card suggestion"><span className="section-kicker">SUGGESTED FOR YOU</span><h2>Based on your assets</h2>{suggestions.map((industry) => <div className="industry-row" key={industry.id}><div><strong>{industry.name}</strong><small>Suggested by {industry.suggestedBy.join(' and ')}</small></div><button className="button subtle" onClick={() => onToggle(industry.id)}>Follow</button></div>)}<p className="muted">Suggestions are never followed automatically.</p></section><section className="industry-card manual-industries"><span className="section-kicker">EXPLORE INDUSTRIES</span><h2>Follow manually</h2><p className="muted">Add a theme even when it is not linked to a current asset.</p>{manualChoices.map((industry) => <div className="industry-row" key={industry.id}><strong>{industry.name}</strong><button className="button subtle" onClick={() => onToggle(industry.id)}>Follow</button></div>)}</section></div>
}

function LotsPanel({ asset, onClose, onSaved }: { asset: Asset; onClose: () => void; onSaved: () => Promise<void> }) {
  const [lots, setLots] = useState<Lot[]>(asset.lots); const [saving, setSaving] = useState(false); const [confirmingRemoval, setConfirmingRemoval] = useState(false)
  const updateLot = (id: string, field: keyof Lot, value: string) => setLots((current) => current.map((lot) => lot.id === id ? { ...lot, [field]: value } : lot))
  const valid = lots.every((lot) => Number(lot.quantity) > 0 && Number(lot.purchasePrice) > 0)
  const save = async () => { if (!valid) return; setSaving(true); await mockApi.updateLots(asset.id, lots); await onSaved(); setSaving(false) }
  const quantity = lots.reduce((sum, lot) => sum + Number(lot.quantity || 0), 0); const average = quantity ? lots.reduce((sum, lot) => sum + Number(lot.quantity || 0) * Number(lot.purchasePrice || 0), 0) / quantity : 0
  const remove = async () => { setSaving(true); await mockApi.deleteAsset(asset.id); await onSaved(); setSaving(false); onClose() }
  return <aside className="side-panel"><button className="close-button" onClick={onClose} aria-label="Close asset management">×</button><span className="section-kicker">MANAGE ASSET</span><h2>{asset.name}</h2><p className="muted">{asset.ticker} · {asset.exchange} · {asset.type}</p>{asset.type === 'Index' ? <p className="panel-note">Indices are followed for market context and cannot be marked as owned.</p> : <><h3>Active purchase lots</h3><p className="muted">Adjust or remove lots to reflect a partial sale. Sell history is outside this MVP.</p><div className="lots">{lots.map((lot, index) => <div className="lot-row" key={lot.id}><span>Lot {index + 1}</span><label>Qty<input aria-label={`Lot ${index + 1} quantity`} value={lot.quantity} inputMode="decimal" onChange={(event) => updateLot(lot.id, 'quantity', event.target.value)} /></label><label>Price<input aria-label={`Lot ${index + 1} price`} value={lot.purchasePrice} inputMode="decimal" onChange={(event) => updateLot(lot.id, 'purchasePrice', event.target.value)} /></label><button className="icon-button" onClick={() => setLots((current) => current.filter((item) => item.id !== lot.id))} aria-label={`Remove lot ${index + 1}`}>×</button></div>)}</div><button className="text-button" onClick={() => setLots((current) => [...current, { id: crypto.randomUUID(), quantity: '', purchasePrice: '' }])}>+ Add lot</button><div className="lot-total"><span>Total quantity<strong>{quantity || '—'}</strong></span><span>Weighted average<strong>{quantity ? money(average, asset.currency) : '—'}</strong></span></div><button className="button primary full" disabled={!valid || saving} onClick={save}>{saving ? 'Saving…' : 'Save lots'}</button></>}<div className="remove-zone"><h3>Stop following this asset</h3><p>It will leave your watchlist. Previously stored timeline data remains in your personal archive.</p>{confirmingRemoval ? <div className="remove-confirm"><span>Remove {asset.ticker} from the watchlist?</span><button className="button danger" disabled={saving} onClick={() => void remove()}>{saving ? 'Removing…' : 'Remove asset'}</button><button className="text-button" onClick={() => setConfirmingRemoval(false)}>Cancel</button></div> : <button className="button danger-outline" onClick={() => setConfirmingRemoval(true)}>Remove from watchlist</button>}</div></aside>
}

function AssetModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => Promise<void> }) {
  const [status, setStatus] = useState<'Owned' | 'Interested'>('Interested'); const [query, setQuery] = useState(''); const [results, setResults] = useState<AssetSearchResult[]>([]); const [selected, setSelected] = useState<AssetSearchResult | null>(null); const [searching, setSearching] = useState(true); const [saving, setSaving] = useState(false)
  useEffect(() => { let active = true; setSearching(true); void mockApi.searchAssets(query).then((next) => { if (active) { setResults(next); setSearching(false) } }); return () => { active = false } }, [query])
  const choose = (asset: AssetSearchResult) => { setSelected(asset); setQuery(asset.name); setStatus('Interested') }
  const save = async (event: React.FormEvent) => { event.preventDefault(); if (!selected) return; setSaving(true); await mockApi.addAsset({ name: selected.name, ticker: selected.ticker, exchange: selected.exchange, type: selected.type, status: selected.type === 'Index' ? 'Interested' : status, lots: [], industries: [] }); await onSaved(); setSaving(false) }
  return <div className="modal-backdrop" role="presentation"><form className="modal" onSubmit={save}><button type="button" className="close-button" onClick={onClose} aria-label="Close add asset form">×</button><span className="section-kicker">WATCHLIST</span><h2>Add an asset</h2><p className="muted">Search the mocked asset lookup and select a valid result.</p><label>Search assets<input value={query} onChange={(event) => { setQuery(event.target.value); setSelected(null) }} placeholder="Search by name or ticker" autoFocus /></label><div className="search-results" aria-live="polite">{searching ? <span>Searching…</span> : results.length ? results.map((asset) => <button type="button" key={`${asset.ticker}-${asset.exchange}`} className={selected?.ticker === asset.ticker ? 'search-result selected' : 'search-result'} onClick={() => choose(asset)}><strong>{asset.name}</strong><span>{asset.ticker} · {asset.exchange} · {asset.type}</span></button>) : <span>No matching assets found.</span>}</div>{selected && <div className="selected-asset"><span>Selected</span><strong>{selected.name}</strong><small>{selected.ticker} · {selected.exchange} · {selected.type}</small></div>}{selected?.type !== 'Index' && <fieldset><legend>Follow status</legend><label className="radio"><input type="radio" checked={status === 'Interested'} onChange={() => setStatus('Interested')} name="status" /> Interested</label><label className="radio"><input type="radio" checked={status === 'Owned'} onChange={() => setStatus('Owned')} name="status" /> Owned</label></fieldset>}{selected?.type === 'Index' && <p className="panel-note">Indices are followed for context and cannot be marked as owned.</p>}<button className="button primary full" disabled={!selected || saving}>{saving ? 'Adding…' : 'Add to watchlist'}</button></form></div>
}

function TimelineView({ assets }: { assets: Asset[] }) {
  const initial = iso(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)); const [selected, setSelected] = useState(initial); const [day, setDay] = useState<TimelineDay | null>(null); const [loading, setLoading] = useState(false)
  useEffect(() => { void loadDay(initial) }, [])
  const dates = useMemo(() => Array.from({ length: 30 }, (_, index) => { const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - index); return iso(date) }), [])
  async function loadDay(date: string) { setSelected(date); setLoading(true); const result = await mockApi.getTimeline(date); setDay(result); setLoading(false) }
  return <section className="page timeline-page"><div className="eyebrow">PERSISTENT PERSONAL ARCHIVE</div><div className="page-heading"><div><h1>See the day<br /><em>as it unfolded.</em></h1><p>Choose a recent date. New days are loaded once and kept in your archive.</p></div></div><div className="timeline-layout"><aside className="calendar-card"><div className="calendar-head"><h2>Last 30 days</h2><span>Stored <i /></span></div><div className="date-grid">{dates.map((date) => <button key={date} className={`${selected === date ? 'selected ' : ''}${mockApi.isArchived(date) ? 'archived' : ''}`} onClick={() => void loadDay(date)} aria-label={`Load ${dateLabel(date)}`}><small>{new Date(`${date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short' })}</small><strong>{new Date(`${date}T12:00:00`).getDate()}</strong></button>)}</div><p className="calendar-note"><i /> Stored archive day &nbsp; · &nbsp; Other dates load on first open</p></aside><section className="day-view"><div className="day-title"><div><span className="section-kicker">SELECTED DAY</span><h2>{dateLabel(selected)}</h2></div>{day && <span className="chip neutral">{day.source === 'archive' ? 'Loaded from archive' : 'Newly retrieved'}</span>}</div>{loading ? <div className="day-loading"><span className="loader" /> Loading and saving this day’s context…</div> : day?.marketClosed ? <div className="closed-state"><span>◷</span><h3>No market-day data</h3><p>This selected date is a weekend. Market data may be unavailable, and no context was retrieved.</p></div> : day && <><div className="timeline-movements">{day.assets.map((asset) => <div key={asset.id}><span>{asset.ticker}</span><strong className={asset.changePercent >= 0 ? 'positive' : 'negative'}>{pct(asset.changePercent)}</strong></div>)}</div><div className="timeline-news"><NewsGroup title="Relevant news" description="Articles available for this trading date." articles={day.articles} /></div><p className="timeline-footnote">Article publication times and exchange trading dates may differ. Linked reports provide possible context, not proof of causality.</p></>}</section></div></section>
}
