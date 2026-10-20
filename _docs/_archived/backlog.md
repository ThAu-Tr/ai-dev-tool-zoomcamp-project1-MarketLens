# MarketLens MVP Backlog

## 1. View the stored dashboard

Goal: Show the demo user's stored dashboard through `GET /api/dashboard`.

Description: Return an empty dashboard when no assets are followed and a populated dashboard when persisted watchlist data exists. Replace the frontend dashboard mock call with the API call and cover the empty and populated responses with tests.

## 2. Search the supported asset catalogue

Goal: Let a user find a valid Stock, ETF, or Index before adding it to the watchlist.

Description: Implement `GET /api/assets/search?q=...` to return matching name, ticker, exchange, and asset-type metadata through a provider adapter or a deterministic development catalogue. The frontend search field must show selectable results and reject submission when no result is selected.

## 3. Add an Interested asset to the watchlist

Goal: Add a selected Stock, ETF, or Index as an Interested watchlist asset.

Description: Implement `POST /api/assets`, persist the selected asset with its stable identifier and exchange metadata, and return the resulting Asset response. An Index must be accepted only as Interested, and duplicate or invalid requests must return the documented validation response.

## 4. Add an Owned Stock or ETF to the watchlist

Goal: Add a selected Stock or ETF with the Owned follow status.

Description: Persist the Owned state through `POST /api/assets` and show the resulting status in the unified watchlist and dashboard. The behavior must exclude Indices and preserve the same asset identity fields used for Interested assets.

## 5. Change an asset's follow status

Goal: Change a followed Stock or ETF between Interested and Owned.

Description: Implement `PATCH /api/assets/{assetId}` for the status change and return the updated Asset. The frontend must refresh the affected watchlist/dashboard state and show validation feedback if an Index is incorrectly changed to Owned.

## 6. Record active purchase lots for an owned asset

Goal: Save multiple active purchase lots and show the owned position totals.

Description: Implement `PUT /api/assets/{assetId}/lots` to persist the complete active-lot list for an Owned Stock or ETF. Return the updated Asset so the frontend can display total quantity and weighted-average purchase price without using binary floating-point calculations.

## 7. Adjust or remove an active purchase lot

Goal: Let a user reflect a partial sale by editing or removing an active lot.

Description: Reuse the complete-lot replacement behavior to validate and save an edited or shortened active-lot list. Keep this explicitly limited to active positions: no sell history, realized gains/losses, or transaction accounting is introduced.

## 8. Remove an asset from the watchlist

Goal: Stop monitoring an asset after an explicit confirmation.

Description: Implement `DELETE /api/assets/{assetId}` to remove the watchlist asset and its active lots while retaining already loaded historical timeline records. The frontend confirmation must name the asset and remove it from the dashboard and watchlist after a successful response.

## 9. Follow and unfollow industries

Goal: Let a user manually control the industries used for news context.

Description: Implement `GET /api/industries` and `PUT /api/industries/{industryId}/follow` to list, follow, and unfollow available industries. The frontend must support both manually chosen industries and asset-derived suggestions, without automatically following a suggestion.

## 10. Show industry suggestions for followed assets

Goal: Suggest relevant industries without changing the user's followed set automatically.

Description: Derive suggestions from persisted asset and ETF metadata, including an explanation of which followed asset supports each suggestion. For ETFs, maintain the lightweight metadata needed for this behavior: tracked index or theme, sector or industry tags, and selected major holdings. Return that relationship in the Industry response and test that a suggestion remains unfollowed until the user chooses it.

## 11. Refresh recent prices for followed assets

Goal: Update stored price snapshots only when newer market data is available.

Description: Implement the price portion of `POST /api/refresh` using a provider adapter, provider watermarks, and persisted snapshots. Fetch only data newer than the last successful refresh and reuse stored values when no newer snapshot exists. The dashboard must preserve prior prices if the provider fails and display the last successful refresh time.

## 12. Show relevant direct asset news

Goal: Show newly retrieved articles that directly concern followed assets.

Description: During refresh, retrieve permitted article metadata, deduplicate it, apply direct asset rule matching, and persist the article-to-asset link. Store only headline, URL, source, timestamp, supplied snippet, relevance, and linked assets or industries; never store full article text. The dashboard must display headline, source, timestamp, snippet, relevance label, and publisher URL.

## 13. Show industry and broader market context

Goal: Surface relevant industry news and wider events alongside the watchlist.

Description: Classify stored article metadata as Industry news, Market context, or Not Relevant using deterministic rules and the LLM only for ambiguous candidates, including candidates whose relevance level is uncertain. The dashboard must show the first two categories separately and exclude Not Relevant articles from the monitoring view.

## 14. Show uncertainty-aware AI market context

Goal: Explain possible links between a price movement and the relevant stored articles.

Description: Generate and persist a short source-linked context summary for an asset when meaningful price and article data exists. Each summary must preserve links to its supporting stored articles so the user can assess the interpretation. The response and UI must use qualified language, include the required disclaimer, and never make investment recommendations or definitive causal claims.

## 15. Load a historical market day on first visit

Goal: Let a user request a date within the initial 30-day historical window.

Description: Implement `GET /api/timeline?date=YYYY-MM-DD` to retrieve, classify, and persist the selected day's available price, article, and context data when it is not already archived. Initial requests outside the preceding 30-day window must be rejected unless that day is already archived. Return an explicit no-market-data result for weekends, holidays, or unavailable data rather than treating it as a generic error.

## 16. Revisit an archived historical market day

Goal: Show a previously loaded timeline day without calling external providers again.

Description: Make the historical endpoint return the persisted day with source `archive` after its initial successful load. The frontend must distinguish archived data from newly loaded data and preserve the original date's linked articles and AI context.

## 17. Handle refresh and history provider failures

Goal: Keep previously stored monitoring data useful when an external provider is unavailable.

Description: Return the documented provider-error response for failed refresh or lazy-history requests while retaining any previously persisted data. The frontend must show a retryable error state and must not imply that newly retrieved data is complete.
