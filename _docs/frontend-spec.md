# MarketLens Frontend Specification

## 1. Purpose and scope

This document specifies the MVP user interface for MarketLens. It translates `_docs/plan.md` and `_docs/architecture.md` into screens, interactions, states, and API expectations for the React frontend.

The interface helps an everyday investor answer:

1. What do I follow?
2. What moved?
3. What happened around it?
4. How can I look back and understand it later?

The frontend is a React and TypeScript single-page application built with Vite. It renders data supplied by the FastAPI JSON API; it never calls data providers, OpenAI, or PostgreSQL directly.

## 2. Product principles

- **Context before conclusion.** Show prices beside relevant news and AI interpretation, not as an isolated price tracker.
- **Interpretation is not fact.** AI copy must use uncertainty-aware language and link users to source articles.
- **One watchlist, clear ownership.** Owned and Interested assets appear together, distinguished by a status badge.
- **Simple daily use.** Stored data appears immediately; manual refresh is visible and intentional.
- **History is a first-class view.** A user can revisit loaded days and request an unvisited date within the allowed 30-day window.
- **No investment advice.** The UI must not use Buy, Hold, Sell, recommendations, targets, or artificial confidence percentages.

## 3. Information architecture

The application has three primary destinations:

```text
Dashboard  ── current watchlist, price movement, news, AI context
Watchlist  ── assets, ownership lots, and followed industries
Timeline   ── calendar and a selected historical day
```

The desktop layout uses a persistent top navigation. On narrow screens, use a compact navigation control that still exposes all three destinations.

Global controls:

- application name: **MarketLens**;
- navigation to Dashboard, Watchlist, and Timeline;
- a Refresh button on the Dashboard;
- displayed last successful refresh time; and
- a consistent user-visible error area for failed saves or data loads.

## 4. Shared UI conventions

### Status and relevance labels

Use text labels in addition to colour so the meaning is accessible:

| Concept | Required label |
| --- | --- |
| Asset follow state | `Owned` or `Interested` |
| Asset type | `Stock`, `ETF`, or `Index` |
| Article relevance | `Direct asset news`, `Industry news`, or `Market context` |
| Price movement | signed percentage and a textual direction such as `Up` or `Down` |
| Data freshness | a timestamp such as `Last refreshed 10:42` |

Positive/negative colours may support price movement but must not be the only indicator. Price movement is descriptive, not advice.

### Article cards and external links

An article card contains only stored metadata:

- headline;
- source;
- publication time in the user-facing timezone;
- relevance label;
- linked assets and/or industries where available; and
- supplied snippet, when available.

Selecting an article opens the publisher URL in a new tab. Do not display or fetch full article text in the frontend.

### AI context card

Every AI context card must:

- be visually labelled `AI-generated context`;
- use qualified wording such as `may be related to`, `possible context`, or `may have contributed`;
- show the relevant price movement and linked source articles; and
- include this persistent disclaimer near the first visible AI card on each relevant screen:

> AI-generated market context may be incomplete or incorrect. Verify important conclusions using the linked sources.

No context card is shown when there is no stored summary. Never invent a placeholder explanation.

## 5. Screens and flows

### 5.1 First-use empty state

The initial Dashboard has no watchlist data. It explains the next action succinctly:

```text
Start your MarketLens watchlist
Add a stock, ETF, or major index to see market movements in context.
[Add asset]
```

`Add asset` navigates to the Watchlist and opens the add-asset form. The first-use flow is:

1. Add a stock, ETF, or index.
2. For a stock or ETF, select `Owned` or `Interested`.
3. If Owned, optionally add one or more active purchase lots.
4. Review industry suggestions and select any to follow.
5. Return to the Dashboard and refresh when ready.

### 5.2 Dashboard

The Dashboard is the default route and combines price data with context. It shows stored data immediately; it does not automatically trigger provider requests when opened.

#### Header

The header contains:

- title `Dashboard`;
- last successful refresh time, or `Not refreshed yet`;
- Refresh button; and
- a short explanation that refresh retrieves only newer available data.

While refresh is in progress, disable the button, show `Refreshing…`, and keep the previous dashboard visible. When it completes, refresh dashboard data. If it fails, retain the previous data and show an actionable error message.

#### Asset overview

Show each followed asset in a compact row or card with:

- name and ticker;
- asset type;
- Owned/Interested badge; indices are shown as followed context assets and cannot be Owned;
- latest price, currency, as-of time, and signed recent movement;
- for Owned assets, total active quantity and weighted-average purchase price; and
- a clear action to open the asset detail/manage view.

The dashboard does not calculate or label portfolio performance, gains/losses, allocation, targets, or recommendations.

#### Context feed

Below or beside the asset overview, show relevant stored information grouped in this order:

1. Direct asset news;
2. Industry news; and
3. Broader market context.

Each group has an empty state rather than disappearing silently, for example: `No relevant industry news is stored for your followed industries yet.` Article cards may be associated with more than one followed item, but the same article should not be repeated unnecessarily in one visible feed.

#### AI market context

Show concise context cards near the associated asset movement or in a dedicated section below the context feed. Each card includes its linked articles. If a summary is unavailable because the provider or AI request failed, show no summary and do not treat absence as a dashboard error.

### 5.3 Watchlist

The Watchlist is the management view for assets, purchase lots, and followed industries. It has two sections or tabs: **Assets** and **Industries**.

#### Assets section

Show a unified list of Stocks, ETFs, and Indices. Include:

- search/filter by followed asset name or ticker;
- `Add asset` action;
- type and follow-status labels; and
- an action to manage or remove the asset.

##### Add asset

The form must require selection of a valid asset returned by the backend's asset search/lookup flow. It collects:

- asset selection, including name, ticker, exchange/market, and type;
- `Owned` or `Interested` for Stocks and ETFs; and
- `Interested`/followed context for Indices only.

Do not let a user mark an Index as Owned. Show backend validation messages next to the relevant field.

##### Asset detail and ownership lots

The detail view shows stable asset information, follow status, and its linked industry suggestions. For Owned Stocks and ETFs, show an **Active purchase lots** section:

- each lot has quantity and purchase price;
- users can add, edit, or remove active lots;
- the UI displays calculated total quantity and weighted-average purchase price returned by the API; and
- explain that sell history and realized gains/losses are outside the MVP, so a partial sale is represented by editing or removing an active lot.

Price and quantity inputs must be validated as positive decimal values. The frontend treats values as strings for input/display and lets the backend perform authoritative exact-decimal calculations.

The detail view also contains a visually distinct `Remove from watchlist` action for every asset type. It requires an in-panel confirmation that names the asset before removal. Removing an asset removes it and its active purchase lots from the watchlist; already stored historical timeline data remains available in the personal archive.

#### Industries section

Show followed industries and a separate suggestion area. The user can:

- follow a suggested industry;
- manually find and follow an available industry; and
- unfollow an industry.

Suggestions show which followed assets support the suggestion where that information is available. Suggested industries are never automatically followed.

### 5.4 Timeline

The Timeline allows a user to understand a selected past market day.

#### Calendar and date selection

Show a calendar/date picker with:

- the previous 30 calendar days selectable for a first request;
- dates outside that window disabled unless the date is already available in the stored archive;
- a visual distinction for days already stored; and
- a selected date summary.

If the selected day is not stored, explain that MarketLens will retrieve and save available data for that day. Show an in-progress state while the request completes. If the date is a weekend, market holiday, or has no returned data, present that result plainly rather than showing a generic error.

#### Day view

For the selected date, show:

- selected date and whether data was loaded from the archive or newly retrieved;
- price movement for followed assets that have data for that market day;
- relevant direct asset, industry, and broader-context article groups;
- linked industries where relevant; and
- available AI context cards plus the disclaimer.

The day view must make it clear that publication time and the relevant market trading date can differ. It must not imply that an article definitely caused a movement.

## 6. API-facing frontend contract

The final OpenAPI document is the source of truth. Until it is generated, the frontend should be developed against mock service functions that mirror these endpoint groups:

| Need | API group | Frontend behaviour |
| --- | --- | --- |
| Dashboard | `GET /api/dashboard` | Load on Dashboard entry and after a successful refresh. |
| Assets | `GET /api/assets/search?q=...`, `GET/POST/PATCH/DELETE /api/assets` | Look up valid assets, then list, add, update, and remove watchlist assets. |
| Purchase lots | `PUT /api/assets/{asset_id}/lots` | Persist the complete active-lot list; reload the returned calculation. |
| Industries | `GET /api/industries`, `PUT /api/industries/{industry_id}/follow` | Render followed industries, suggestions, and follow actions. |
| Refresh | `POST /api/refresh` | Block duplicate refresh clicks, show progress, then reload dashboard. |
| History | `GET /api/timeline?date=YYYY-MM-DD` | Render stored day or show the lazy-load progress/result. |

The API client must present server validation errors, unavailable-provider errors, and unexpected errors distinctly. It must not expose provider credentials or provider-specific raw responses in the UI.

## 7. UI states and failure handling

Every data-dependent screen needs the following states:

| State | Expected UI behaviour |
| --- | --- |
| Initial loading | Use meaningful skeletons or concise loading text; do not render misleading zero values. |
| Empty | Explain why no data exists and offer the relevant next action. |
| Refresh/loading in progress | Preserve already displayed data and disable duplicate submission. |
| Validation error | Keep entered form values; show the field-level server error. |
| Provider/AI failure | Preserve stored results; identify the unavailable action or data without claiming new data is complete. |
| Network/unexpected failure | Show a retry action and retain the user’s current route and input where possible. |
| No market-day data | Explain that the selected date may be a weekend, holiday, unsupported exchange date, or have no available provider data. |

## 8. Responsive and accessible behaviour

- Support keyboard navigation, visible focus indicators, semantic buttons, labelled form controls, and descriptive external-link text.
- Do not convey price direction, ownership, or relevance using colour alone.
- Render charts with an adjacent textual summary of the date range, current value, and movement.
- Ensure forms are usable on narrow screens: labels remain visible, decimal inputs have clear currency context, and primary actions remain reachable.
- Keep article links, provider errors, and AI disclaimers readable without hover-only interactions.

## 9. Explicit frontend exclusions

The MVP frontend does not include:

- login, registration, accounts, or profile management;
- broker, bank, or trading connections;
- Buy/Hold/Sell recommendations, price targets, confidence scores, or portfolio advice;
- sell transactions, realized gains/losses, tax, dividends, or advanced analytics;
- alerts, email, push notifications, background monitoring, or real-time ticks;
- crypto or individual bonds;
- full article reader pages, stored article text, publisher scraping, or custom news sources;
- unlimited historical search, economic calendars, earnings calendars, or social features; and
- editable full ETF holdings or continuous holding-weight updates.

## 10. Prototype and acceptance checklist

Before backend integration, the React prototype should use realistic mock data and demonstrate these flows:

- add an Interested Stock/ETF or a followed Index;
- add an Owned Stock/ETF with multiple lots and display aggregate values;
- remove an asset from the watchlist through a confirmation step;
- view and act on, but do not auto-accept, industry suggestions;
- view a combined dashboard with price changes, three relevance levels of news, source links, and qualified AI context;
- display a refresh progress and failure state;
- select an already-loaded timeline day;
- select a not-yet-loaded date within 30 days and display its loading state and result; and
- handle empty, validation, provider-error, and non-trading-day states.

The prototype is successful when all core flows are understandable without live data and the interface never implies that a relationship or recommendation is certain.
