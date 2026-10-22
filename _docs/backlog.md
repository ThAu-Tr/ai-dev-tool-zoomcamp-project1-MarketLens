# MarketLens MVP Backlog — Refined

This is a one-session-sized revision of [_docs/backlog.md](backlog.md). The original backlog remains unchanged for comparison.

## 1. View the stored dashboard
Goal: Show the demo user's stored dashboard when they open the app.
Description: Implement `GET /api/dashboard` so the dashboard shows its empty or populated state with the saved assets, prices, and followed industries. Replace the corresponding frontend mock call and cover both states with tests.

## 2. Search the supported asset catalogue
Goal: Let a user find a valid asset before adding it.
Description: Implement `GET /api/assets/search` to return matching supported stocks, ETFs, and indices with the metadata needed by the picker. The interface must show useful matching results and prevent a user from selecting an unsupported symbol or an arbitrary free-text entry.

## 3. Add a selected asset to the watchlist
Goal: Let a user add a selected stock or ETF as Owned or Interested.
Description: Implement `POST /api/assets` and its form flow, validating that the selection came from the supported catalogue and that only stocks and ETFs can be Owned. Persist the chosen status and show the new asset immediately on the dashboard, including clear validation feedback.

## 4. Change an asset's ownership status
Goal: Let a user switch an existing stock or ETF between Owned and Interested.
Description: Implement `PATCH /api/assets/{assetId}` and the associated control, enforcing that indices remain Interested and that an Owned asset has at least one active lot. The dashboard must reflect the updated status without losing the asset's other saved information.

## 5. Manage an owned asset's active purchase lots
Goal: Let a user record, correct, or remove the active lots behind an Owned stock or ETF.
Description: Implement the lots editor and `PUT /api/assets/{assetId}/lots`, validating exact positive quantities and prices, purchase dates, and at least one lot for an Owned asset. Save the complete active-lot list atomically and recalculate the position information displayed on the dashboard.

## 6. Remove an asset from the watchlist
Goal: Let a user permanently remove an asset they no longer follow.
Description: Implement a confirmation flow and `DELETE /api/assets/{assetId}` that removes the asset, its active lots, and its asset-specific saved context from the dashboard. The success state and an error state must both leave the remaining watchlist usable.

## 7. Manage followed industries
Goal: Let a user follow or unfollow industries from the available list.
Description: Implement `GET /api/industries` and `PUT /api/industries/{industryId}/follow` so the interface clearly distinguishes followed industries from available options. Persist the follow state and update the dashboard's industry context without affecting the user's tracked assets.

## 8. Suggest industries from the watchlist
Goal: Offer relevant industry suggestions for the user's tracked stocks and ETFs.
Description: Derive suggestions from stored asset and fund metadata, omit industries already followed, and return them through the industries view. For ETFs, maintain the lightweight tracked-index or theme, sector or industry tags, and selected-major-holdings metadata needed to make those suggestions. The user must be able to accept a suggestion using the same follow behavior as a manually selected industry.

## 9. Refresh current asset prices
Goal: Update the watchlist with the latest available prices.
Description: Implement `POST /api/refresh` to fetch only prices newer than the last successful refresh through the market-data provider adapter, store a timestamped result, and render it on the dashboard. Reuse stored values when no newer price is available. If the provider is unavailable or incomplete, retain the last successful values and show an honest stale or unavailable state rather than inventing data.

## 10. Refresh direct news for followed assets
Goal: Show recent, relevant news for each tracked asset.
Description: During refresh, retrieve, deduplicate, persist, and display articles that directly match each selected asset, with links and source timestamps. Store only permitted metadata—headline, URL, source, publication time, supplied snippet, relevance, and links—not full article text. Handle an individual source failure without discarding previously stored articles or preventing the rest of the refresh from completing.

## 11. Show classified industry news
Goal: Show recent news relevant to industries the user follows.
Description: During refresh, classify retrieved articles against the followed industries using deterministic matching rules, with the LLM fallback for ambiguous relevance or category decisions, then store and render the industry context. Exclude duplicates and articles that do not meet the relevance rules, and retain uncertainty where classification is not clear.

## 12. Show broader market context
Goal: Show relevant market-wide news separately from asset and industry news.
Description: During refresh, classify broader articles as Market context using deterministic signals and the approved uncertainty-aware AI fallback for ambiguous cases, including distinctions between Industry news, Market context, and Not Relevant. Persist the category and evidence needed for the interface, while excluding irrelevant articles and avoiding definitive causal claims.

## 13. Generate AI market context
Goal: Provide concise, uncertainty-aware AI summaries of the available market context.
Description: Use the existing stored price and article context to produce bounded summaries with clear uncertainty and no investment advice. Each summary must retain links to its supporting articles and the UI must show the required uncertainty disclaimer. Keep the provider call behind an adapter, persist only the result needed by the dashboard, and show a safe unavailable state if generation fails.

## 14. Load a historical day's price movement
Goal: Let a user open a previous market day and see its stored or newly retrieved price movement.
Description: Implement `GET /api/timeline?date=YYYY-MM-DD` so a first visit within the preceding 30 days lazily loads and stores the selected day's price information, while a later visit reuses the saved snapshot. Reject an unarchived date outside that initial window. The timeline must distinguish a normal result from a market-closed or provider-unavailable date.

# Post-MVP Backlog

## 15. Add relevant news and context to a historical day
Goal: Let a historical day explain the news context available for that date.
Description: For a selected historical day, retrieve or reuse relevant articles, classify them into the same asset, industry, and market categories, and persist the resulting context with that day's snapshot. Show only supported evidence and label incomplete context when a source or classification is unavailable.

## 16. Revisit an archived market day
Goal: Let a user return to a previously loaded day without changing its saved record.
Description: Reopen the stored price snapshot, categorized articles, and AI context for a selected date through the timeline interface. This view must use persisted data only, make no new provider calls, and clearly distinguish an archived record from current dashboard data.
