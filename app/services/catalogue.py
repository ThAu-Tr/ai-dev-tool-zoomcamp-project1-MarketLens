from __future__ import annotations

from app.repositories.catalogue import AssetCatalogueRepository
from app.schemas import AssetSearchResult


class AssetCatalogueService:
    """Search selectable assets without calling any external provider."""

    def __init__(self, repository: AssetCatalogueRepository) -> None:
        self.repository = repository

    def search(self, query: str) -> list[AssetSearchResult]:
        normalized_query = query.strip().casefold()
        if not normalized_query:
            raise ValueError("Query must contain at least one non-whitespace character.")

        results: list[AssetSearchResult] = []
        seen: set[tuple[str, str]] = set()
        for entry in self.repository.entries():
            try:
                result = AssetSearchResult.model_validate(entry)
            except ValueError:
                continue

            key = (result.ticker.casefold(), result.exchange.casefold())
            haystack = f"{result.name} {result.ticker}".casefold()
            if key not in seen and normalized_query in haystack:
                seen.add(key)
                results.append(result)
        return results
