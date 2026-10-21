from datetime import UTC, datetime
from decimal import Decimal

from app.models import Article, Asset, DemoUser, RefreshState
from app.providers import MarketQuote, NewsArticle
from tests.test_dashboard import build_client
from tests.test_refresh import session_factory  # noqa: F401 - pytest fixture


class FakeNewsProvider:
    def __init__(self, articles: list[NewsArticle], *, news_error: Exception | None = None) -> None:
        self.articles = articles
        self.news_error = news_error
        self.news_calls: list[tuple[list[str], datetime | None]] = []

    def fetch_market_data(self, tickers: list[str], since: datetime | None) -> list[MarketQuote]:
        return [MarketQuote(ticker, Decimal("101"), "EUR", Decimal("1"), datetime(2026, 10, 21, 10, tzinfo=UTC)) for ticker in tickers]

    def fetch_news(self, tickers: list[str], since: datetime | None) -> list[NewsArticle]:
        self.news_calls.append((tickers, since))
        if self.news_error:
            raise self.news_error
        return self.articles


def seed_assets(session_factory) -> None:
    with session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.add_all([
            Asset(id="sap", user_id=1, name="SAP SE", ticker="SAP", exchange="XETRA", asset_type="Stock", status="Interested", industries=[]),
            Asset(id="asml", user_id=1, name="ASML Holding", ticker="ASML", exchange="AMS", asset_type="ETF", status="Interested", industries=[]),
            Asset(id="dax", user_id=1, name="DAX", ticker="DAX", exchange="XETRA", asset_type="Index", status="Interested", industries=[]),
        ])


def news(headline: str, identifiers: list[str], *, url: str = "https://news.example/direct", identity: str | None = "wire-1", snippet: str | None = "Provider supplied context.") -> NewsArticle:
    return NewsArticle(headline=headline, source="Wire", published_at=datetime(2026, 10, 21, 9, tzinfo=UTC), url=url, identifiers=identifiers, source_identity=identity, snippet=snippet)


def test_refresh_saves_only_explicit_direct_matches_deduplicates_and_links_all_assets(session_factory):
    seed_assets(session_factory)
    provider = FakeNewsProvider([
        news("SAP and ASML update", ["SAP", "ASML Holding"], url="https://news.example/direct?utm_source=feed"),
        news("Ambiguous SAP mention", [], url="https://news.example/ambiguous", identity="wire-2"),
        news("Sector update", ["Semiconductors"], url="https://news.example/sector", identity="wire-3"),
    ])

    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        articles = session.query(Article).all()
        assert len(articles) == 1
        assert articles[0].assets == ["ASML", "SAP"]
        assert articles[0].url == "https://news.example/direct"
        assert articles[0].snippet == "Provider supplied context."

    repeated = build_client(session_factory, provider).post("/api/refresh")
    assert repeated.status_code == 200
    with session_factory() as session:
        assert session.query(Article).count() == 1
        assert session.get(RefreshState, 1).news_status == "current"
    assert provider.news_calls[1][1] == datetime(2026, 10, 21, 9)


def test_news_failure_preserves_persisted_articles_and_does_not_undo_price_update(session_factory):
    seed_assets(session_factory)
    with session_factory.begin() as session:
        session.add(Article(id="old", user_id=1, headline="Stored", source="Wire", published_at=datetime(2026, 10, 20, 9), relevance="Direct asset news", assets=["SAP"], industries=[], snippet=None, url="https://news.example/old"))
    response = build_client(session_factory, FakeNewsProvider([], news_error=TimeoutError("provider token=secret"))).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        assert session.query(Article).count() == 1
        assert session.get(Asset, "sap").price == Decimal("101.000000")
        assert session.get(RefreshState, 1).news_status == "stale"
    dashboard = build_client(session_factory).get("/api/dashboard").json()
    assert dashboard["newsStatus"] == "stale"
    assert dashboard["articles"][0]["snippet"] is None
