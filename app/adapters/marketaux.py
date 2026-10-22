from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.providers import NewsArticle


class MarketauxProvider:
    """Metadata-only adapter for Marketaux's published news endpoint.

    It implements the news portion of ProviderGateway and can be composed with
    another provider for prices. The API's three-result page size bounds each
    request; callers should pass only the user's tracked symbols.
    """

    endpoint = "https://api.marketaux.com/v1/news/all"
    max_results = 3

    def __init__(self, api_key: str | None = None, user_agent: str | None = None, timeout: float = 8.0) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("MARKETAUX_API_KEY") or None
        self.user_agent = user_agent if user_agent is not None else os.getenv("MARKETAUX_USER_AGENT", "MarketLens/0.1")
        self.timeout = timeout

    def fetch_news(self, tickers: list[str], since: datetime | None) -> list[NewsArticle]:
        if not self.api_key:
            return []
        symbols = list(dict.fromkeys(t.strip().upper() for t in tickers if t.strip()))
        if not symbols:
            return []
        params: dict[str, str] = {
            "api_token": self.api_key,
            "symbols": ",".join(symbols),
            "limit": str(self.max_results),
            "language": "en",
        }
        if since is not None:
            if since.tzinfo is None:
                since = since.replace(tzinfo=UTC)
            params["published_after"] = since.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        request = Request(
            f"{self.endpoint}?{urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            # The refresh workflow treats this as an individual news-source failure.
            raise
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("Marketaux returned an invalid news response.")
        return [article for item in payload["data"][: self.max_results] if (article := self._article(item, symbols)) is not None]

    @staticmethod
    def _article(item: Any, requested_symbols: list[str]) -> NewsArticle | None:
        if not isinstance(item, dict):
            return None
        headline = item.get("title") or item.get("headline")
        url = item.get("url")
        raw_date = item.get("published_at")
        source = item.get("source")
        if not all(isinstance(value, str) and value.strip() for value in (headline, url, raw_date, source)):
            return None
        try:
            published_at = datetime.fromisoformat(raw_date.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        entities = item.get("entities")
        identifiers: list[str] = []
        if isinstance(entities, list):
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                symbol = entity.get("symbol")
                if isinstance(symbol, str) and symbol.strip() and symbol.upper() in requested_symbols:
                    identifiers.append(symbol.upper())
        # Industry strings are provider metadata, retained as identifiers for the
        # existing conservative classifier to decide whether they are relevant.
        industries: list[str] = []
        raw_industries = item.get("industries")
        if isinstance(raw_industries, list):
            industries.extend(value.strip() for value in raw_industries if isinstance(value, str) and value.strip())
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict) and str(entity.get("type", "")).casefold() in {"industry", "sector"}:
                    name = entity.get("name")
                    if isinstance(name, str) and name.strip():
                        industries.append(name.strip())
        snippet = item.get("snippet")
        if not isinstance(snippet, str):
            snippet = None
        else:
            snippet = snippet.strip() or None
        identity = item.get("uuid") or item.get("id")
        return NewsArticle(
            headline=headline.strip(), source=source.strip(), published_at=published_at,
            url=url.strip(), identifiers=list(dict.fromkeys(identifiers)),
            source_identity=str(identity) if identity is not None else None, snippet=snippet,
            industry_identifiers=list(dict.fromkeys(industries)),
        )
