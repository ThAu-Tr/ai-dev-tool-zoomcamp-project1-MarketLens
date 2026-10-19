# MarketLens — MVP Scope


## 1. Product Idea

**MarketLens** is a lightweight investment-monitoring tool for everyday users who want to understand how market movements relate to news and broader real-world events.

Users define the assets and industries they care about, refresh the app during the day, and see:

- current price development
- relevant financial news
- broader contextual news
- AI-generated explanations of likely relationships between events and market movements

The app also provides a historical timeline/calendar so users can look back at specific days and understand what happened in the market around that time.

The goal is **not** to provide investment advice or full portfolio management. The goal is to help users monitor and understand assets in context.

---

## 2. Target User
Everyday investors who actively follow stocks and ETFs but do not use professional market terminals. They want a simple way to monitor assets they own or are interested in and understand relevant market and news developments.

--

## 3. Problem Statement
Market prices, financial news, and broader world events are usually spread across different sources. This makes it difficult for everyday investors to understand why assets may be moving and to look back later at the context surrounding those movements. MarketLens brings these pieces together in one place.

--

## 4. Core MVP Experience

The MVP uses a **combined dashboard**.

Users can monitor:

- Stocks
- ETFs
- Major indices

Users can also follow industries/themes separately.

Examples:

- Automotive
- Semiconductors
- Renewable Energy
- Defense
- Banking
- AI

The dashboard combines:

- price development
- asset-related news
- industry-related news
- broader market context
- AI-generated context summaries

---

## 5. Asset Status

Assets can be classified as:

### Owned
Assets the user currently holds.

### Interested
Assets the user wants to monitor but does not currently own.

Owned and Interested are properties of the asset itself and belong in the same asset list.

---

## 6. Owned Positions

For owned assets, the user can enter multiple active purchase lots.

Example:

- 5 shares at €130
- 3 shares at €150
- 2 shares at €160

The app automatically calculates:

- total quantity
- weighted average purchase price

This avoids forcing the user to manually recalculate their position after additional purchases.

### Not included in MVP

- sell transaction history
- realized gains/losses
- full transaction accounting

If the user sells part of a position, they simply adjust or remove the relevant active quantity.

---

## 7. Industry Following

Industries are a separate concept from assets.

Users can:

- manually follow industries
- receive industry suggestions based on followed assets

A single stock or ETF may belong to multiple industries/themes.

Example:

Tesla could reasonably be associated with:

- Automotive
- EVs
- Energy Storage
- AI / Robotics

The app should **suggest** relevant industries rather than automatically add them.

The user chooses which industries to follow.

---

## 8. News Classification

The app should distinguish between different levels of relevance.

### Direct Asset News

News that directly mentions or clearly concerns a followed asset.

Example:

> BMW announces new EV production strategy.

### Industry-Related News

News that affects an industry or theme the user follows.

Example:

> EU announces new rules for EV battery recycling.

### Broader Market Context

News that may indirectly affect followed assets or industries.

Examples:

- interest-rate decisions
- geopolitical events
- trade restrictions
- energy-price shocks
- elections
- major regulation

### Not Relevant

Articles that should not appear in the user's monitoring view.

---

## 9. News-Relevance Approach

The MVP should use a **hybrid classification approach**.

### Rule-based matching

Simple and reliable cases can be matched using:

- company names
- tickers
- ETF names
- industry keywords
- known metadata

### LLM-based classification

An LLM handles more ambiguous cases.

The LLM receives:

- article headline
- article summary/snippet
- followed assets
- followed industries
- relevant ETF metadata

It decides whether the article is:

- Direct Asset News
- Industry-Related News
- Broader Market Context
- Not Relevant

It may also identify which assets or industries are connected to the article.

---

## 10. ETF Handling

ETFs require more context than individual stocks because relevant news may not mention the ETF itself.

For the MVP, each ETF should have lightweight metadata such as:

- ETF name
- tracked index or theme
- sector / industry tags
- selected major holdings

News classification can then use the same hybrid approach as for stocks.

Example:

For a semiconductor ETF, relevant news might concern:

- the ETF itself
- the semiconductor industry
- the index it tracks
- major holdings such as Nvidia, AMD, TSMC, or ASML
- broader events such as chip export restrictions

### Out of scope

- continuously tracking the ETF's complete holdings
- continuously tracking holding weights
- deep ETF portfolio analysis

---

## 11. Dashboard

The dashboard should balance **price information and news context**.

For each followed asset, the user should be able to see:

- current/recent price
- recent price movement
- whether the asset is Owned or Interested
- relevant direct news
- relevant industry/context news

The dashboard should not be price-only or news-only.

The main value is the connection between the two.

---

## 12. Refresh Behavior

The user can manually refresh the app during the day.

The app should not re-fetch everything on every refresh.

Instead:

- fetch only new market data where possible
- fetch only new news since the last successful refresh
- save relevant results in the database
- reuse already stored data
- cache recent API responses where appropriate
- show the last refresh time

This reduces API usage and avoids unnecessary duplicate requests.

---

## 13. Historical Timeline / Calendar

The historical timeline is one of the main differentiating features of MarketLens.

Users can open a calendar and select past days to understand:

- what happened that day
- which followed assets moved
- which relevant news articles were published
- which industries were affected
- what broader context may have contributed to market movement

### Historical window

The MVP exposes the previous **30 days** for historical lookup.

However, it should **not automatically download all 30 days of news**.

Instead, historical data is loaded lazily.

### Lazy historical loading

When the user opens a historical day for the first time:

1. fetch market data for that day
2. fetch relevant news for that day
3. classify and link the news
4. save the resulting metadata in the database

If the user opens the same day again, the app loads it from the database instead of querying the APIs again.

### Growing timeline

Once a historical day has been fetched, it remains available.

The app therefore gradually builds a persistent personal market archive.

The 30-day limitation applies to how far back the user can initially request historical data, not to how long already collected data is retained.

---

## 14. Stored News Data

The MVP should **not store full article text**.

Instead, store only the metadata needed for the timeline:

- headline
- article URL
- source
- publication timestamp
- summary/snippet if supplied by the API
- relevance classification
- linked assets
- linked industries
- generated context summary where applicable

This keeps storage small and avoids unnecessary duplication of publisher content.

---

## 15. News Sources

The MVP should not scrape large numbers of individual news websites.

Instead, use aggregated providers.

Likely provider structure:

### Financial news provider

Used for:

- company news
- ETF news
- market-specific reporting

### General news provider

Used for:

- geopolitics
- regulation
- elections
- energy
- economic policy
- major real-world events

The app then classifies and links those articles to the user's monitored assets and industries.

---

## 16. AI Market Context

The app should generate short AI explanations connecting market movement and relevant news.

Example:

> SAP fell 2.3% today. Possible context includes weaker European technology stocks and recent enterprise-software guidance concerns.

The AI must **not claim certainty about causality**.

Use wording such as:

- may be related to
- possible context
- likely relevant
- may have contributed

Avoid wording such as:

- caused
- definitely resulted from
- the reason was

### AI disclaimer

The interface should clearly indicate that AI-generated explanations may be incomplete or incorrect.

Suggested notice:

> AI-generated market context may be incomplete or incorrect. Verify important conclusions using the linked sources.

The underlying source articles should always remain visible so the user can evaluate the explanation independently.

No artificial confidence percentages should be shown unless a meaningful confidence mechanism exists.

---

## 17. Market Data Providers

The MVP does not need to use one provider for everything.

A reasonable provider strategy is:

- one provider for stocks, ETFs, and major indices
- one provider for financial news
- optionally one provider for broader general news

The exact providers are an architecture/implementation decision.

The goal should be to use the **smallest practical combination of free APIs** that supports the MVP.

---

## 18. Supported Asset Types

### MVP

- Stocks
- ETFs
- Major indices

Examples of indices:

- DAX
- S&P 500
- NASDAQ-100
- Dow Jones
- Euro Stoxx 50

Indices can be followed for market context but cannot be marked as Owned.

### Post-MVP

- Crypto
- Individual bonds

Crypto was intentionally removed from the MVP to avoid:

- additional provider complexity
- 24/7-market handling
- unnecessary scope expansion

Individual bonds were excluded because they often require more specialized pricing, identifiers, yield data, and metadata.

Bond ETFs remain supported because they behave like normal exchange-traded funds.

---

## 19. Main User Flow

### First Use

1. User adds stocks, ETFs, or indices.
2. Stocks and ETFs are marked as:
   - Owned
   - Interested
3. For owned assets, the user may add multiple active purchase lots.
4. The app suggests relevant industries/themes.
5. The user selects industries they want to follow.
6. The user may manually add additional industries.

### Daily Use

1. User opens MarketLens.
2. Dashboard displays stored recent data.
3. User refreshes.
4. App fetches only new price/news data where possible.
5. App classifies new articles.
6. Dashboard updates price movements and relevant news.
7. AI context summaries explain possible relationships.

### Historical Use

1. User opens the timeline/calendar.
2. User chooses a date within the available historical window.
3. If the date has already been fetched:
   - load it from the database.
4. If the date has not been fetched:
   - fetch market data for that date
   - fetch relevant news
   - classify and link the results
   - save them
5. User sees the day's market movements, articles, and AI-generated context.

---

## 20. Technical Challenges to Consider

These do not make the project infeasible, but they should influence implementation decisions.

### Market data coverage

Different providers may offer different coverage for:

- exchanges
- ETFs
- indices
- historical data

### Historical news availability

Historical news access may be limited by:

- free API tiers
- date-range restrictions
- request limits

### News relevance

Determining whether an article is:

- directly asset-related
- industry-related
- broader context
- irrelevant

requires a combination of rules and LLM classification.

### Duplicate news

Different publishers or aggregators may return nearly identical stories.

The app may need basic deduplication.

### Asset identification

Ticker symbols may not be globally unique.

The implementation should consider exchange or another stable identifier where necessary.

### ETF metadata

ETF themes and major holdings can change.

For the MVP, occasional metadata updates are sufficient.

### Time zones and trading days

News timestamps and market trading dates may not align perfectly.

The system needs consistent handling of:

- publication timestamps
- exchange trading dates
- weekends
- holidays

### API limits

Manual refreshing can generate many API calls.

Use:

- caching
- incremental fetching
- lazy historical loading
- stored historical results

to keep usage manageable.

### Provider availability

A provider may fail temporarily or not support a specific asset.

The implementation should avoid assuming perfect coverage.

### Data licensing / terms of use

The final provider choices should be checked for:

- permitted display of market data
- permitted storage of metadata
- permitted display of news snippets
- attribution requirements

---

## 21. Explicitly Out of Scope for MVP

### Asset classes

- Crypto
- Individual bonds

### Portfolio management

- sell transaction history
- realized gains/losses
- tax calculations
- dividend tracking
- portfolio optimization
- diversification scoring
- rebalancing
- advanced risk analytics
- Sharpe ratio
- performance attribution
- benchmark-performance analytics

### Trading and account integration

- broker integrations
- bank integrations
- automatic portfolio synchronization
- buying or selling assets through the app

### Monitoring

- price alerts
- email alerts
- push notifications
- continuous background monitoring
- real-time tick-by-tick market data

### News

- storing full article text
- scraping large numbers of individual publishers
- user-defined/custom news-source integrations
- guaranteeing perfect historical news completeness

### ETFs

- full continuously updated holdings
- continuously updated holding weights
- deep ETF portfolio analysis

### AI

- investment recommendations
- Buy / Hold / Sell recommendations
- definitive causal claims
- fake confidence percentages

### Research tooling

- unlimited historical market research
- Bloomberg-style historical search
- full economic calendar
- full earnings calendar

### Social features

- comments
- public profiles
- shared watchlists
- community recommendations
- following other investors

### Authentication

Authentication / multi-user support is optional and should be omitted from the MVP unless required by the course/project infrastructure.

A single demo user is sufficient for the product concept.

---

## 22. Core Features Summary

The MVP has five core features.

### 1. Asset Watchlist & Ownership

- Stocks, ETFs, major indices
- Owned vs Interested
- multiple active purchase lots
- automatic aggregation of owned positions

### 2. Industry Following

- manually follow industries
- receive industry suggestions from followed assets
- one asset can map to multiple industries

### 3. Combined Monitoring Dashboard

- current/recent price movements
- direct asset news
- industry news
- broader market context
- manual refresh

### 4. Persistent Historical Market Timeline

- select individual historical days
- lazy-load price/news data for that day
- store retrieved metadata
- revisit already loaded historical days without additional API calls

### 5. AI Market Context

- classify news relevance
- link news to assets and industries
- explain possible relationships between events and market movements
- clearly distinguish interpretation from established fact

---

## 23. MVP Product Principle

MarketLens should answer four simple questions:

> **What do I follow?**

> **What moved?**

> **What happened around it?**

> **How can I look back and understand it later?**

Anything that does not meaningfully help answer those questions should be considered post-MVP.
