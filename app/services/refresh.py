from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.providers import MarketDataResult, NewsArticle, ProviderGateway
from app.models import RefreshState
from app.repositories.refresh import RefreshRepository
from app.schemas import RefreshResponse


class ProviderUnavailableError(RuntimeError):
    pass


class RefreshService:
    def __init__(self, repository: RefreshRepository, provider: ProviderGateway | None) -> None:
        self.repository = repository
        self.provider = provider

    def refresh(self) -> RefreshResponse:
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        if self.provider is None:
            self.repository.mark_unavailable(user.id, [asset.ticker for asset in self.repository.assets_for(user.id)])
            self.repository.session.commit()
            raise ProviderUnavailableError("Market data is currently unavailable.")

        assets = self.repository.assets_for(user.id)
        since = self.repository.last_refreshed_at(user.id)
        try:
            result = self.provider.fetch_market_data([asset.ticker for asset in assets], since)
        except Exception as error:
            self.repository.mark_unavailable(user.id, [asset.ticker for asset in assets])
            self.repository.session.commit()
            raise ProviderUnavailableError("Market data is currently unavailable.") from error

        if isinstance(result, MarketDataResult):
            if result.unavailable_tickers:
                self.repository.mark_unavailable(user.id, result.unavailable_tickers)
                self.repository.session.commit()
                raise ProviderUnavailableError("Market data is incomplete; previous values are still shown.")
            quotes = result.quotes
        else:
            quotes = result
            requested = {asset.ticker.upper() for asset in assets}
            covered = {quote.ticker.upper() for quote in quotes}
            missing = sorted(requested - covered)
            if missing and quotes:
                self.repository.mark_unavailable(user.id, missing)
                self.repository.session.commit()
                raise ProviderUnavailableError("Market data is incomplete; previous values are still shown.")
            if missing and since is None and requested:
                self.repository.mark_unavailable(user.id, missing)
                self.repository.session.commit()
                raise ProviderUnavailableError("Market data is unavailable for one or more tracked symbols.")
            requested = {asset.ticker.upper() for asset in assets}
            covered = {quote.ticker.upper() for quote in quotes}
            missing = sorted(requested - covered)
            if missing and quotes:
                self.repository.mark_unavailable(user.id, missing)
                self.repository.session.commit()
                raise ProviderUnavailableError("Market data is incomplete; previous values are still shown.")
            if missing and since is None and requested:
                self.repository.mark_unavailable(user.id, missing)
                self.repository.session.commit()
                raise ProviderUnavailableError("Market data is unavailable for one or more tracked symbols.")
        # A provider may omit a symbol when no newer quote exists. Existing values
        # remain untouched; only normalized, newer quotes are applied.
        newer = [quote for quote in quotes if since is None or _as_utc(quote.as_of) > _as_utc(since)]
        if not newer:
            if since is None:
                raise ProviderUnavailableError("No newer market data is available.")
            state = self.repository.session.get(RefreshState, user.id)
            if state is not None:
                state.status = "stale"
                self.repository.session.commit()
            refreshed_at = _as_utc(since)
        else:
            refreshed_at = max(_as_utc(quote.as_of) for quote in newer)
            self.repository.apply_quotes(user.id, newer, refreshed_at)
            self.repository.session.commit()

        # News availability is intentionally independent of price availability:
        # a failed news call must not roll back successful quote persistence.
        self._refresh_news(user.id, assets)
        return RefreshResponse(lastRefreshedAt=refreshed_at)

    def _refresh_news(self, user_id: int, assets: list[object]) -> None:
        fetch_news = getattr(self.provider, "fetch_news", None)
        if not callable(fetch_news):
            return
        since = self.repository.newest_article_at(user_id)
        try:
            supplied = fetch_news([asset.ticker for asset in assets], since)
        except Exception:
            self.repository.mark_news_status(user_id, "stale")
            self.repository.session.commit()
            return

        malformed = False
        industries = self.repository.followed_industries(user_id)
        for article in supplied:
            if not isinstance(article, NewsArticle) or not _is_valid_article(article):
                malformed = True
                continue
            tickers = _direct_tickers(article, assets)
            url = _canonical_url(article.url)
            identity = article.source_identity or url
            article_id = "news-" + sha256(f"{article.source}|{identity}".encode()).hexdigest()[:32]
            if tickers:
                self.repository.save_direct_article(user_id, article, article_id, url, tickers)
                continue
            matched = _matched_industries(article, industries)
            if matched:
                self.repository.save_industry_article(user_id, article, article_id, url, matched)
        self.repository.mark_news_status(user_id, "stale" if malformed else "current")
        self.repository.session.commit()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _is_valid_article(article: NewsArticle) -> bool:
    # An article without supported identifiers is a valid but irrelevant result,
    # not a malformed provider response. It is simply not saved as direct news.
    return bool(article.headline.strip() and article.source.strip() and article.url.strip() and isinstance(article.published_at, datetime))


def _direct_tickers(article: NewsArticle, assets: list[object]) -> list[str]:
    """Match only exact normalized provider identifiers, never ticker substrings."""
    identifiers = {_normalize_identifier(value) for value in article.identifiers if value.strip()}
    matched: list[str] = []
    for asset in assets:
        ticker = _normalize_identifier(asset.ticker)
        name = _normalize_identifier(asset.name)
        if ticker in identifiers or name in identifiers:
            matched.append(asset.ticker)
    return matched


def _normalize_identifier(value: str) -> str:
    return " ".join(value.casefold().split())


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not key.casefold().startswith("utm_")])
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path, query, ""))


def _matched_industries(article: NewsArticle, industries: list[object]) -> list[str]:
    """Match only explicit persisted followed-industry names in supplied text.

    Word boundaries avoid classifying incidental substrings (for example,
    "AI" inside "said"). Uncertain articles are left unclassified.
    """
    text = f"{article.headline} {article.snippet or ''}".casefold()
    matched: list[str] = []
    for industry in industries:
        name = industry.name.strip()
        if name and re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", text):
            matched.append(industry.id)
    return sorted(set(matched))
