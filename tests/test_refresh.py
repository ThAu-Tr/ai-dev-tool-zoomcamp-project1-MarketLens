from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Article, Asset, DemoUser, Industry, IndustryFollow, RefreshState
from app.providers import MarketDataResult, MarketQuote, NewsArticle, PartialNewsProviderError
from tests.test_dashboard import build_client


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class FakeMarketProvider:
    def __init__(self, quotes: list[MarketQuote] | None = None, error: Exception | None = None) -> None:
        self.quotes = quotes or []
        self.error = error
        self.calls: list[tuple[list[str], datetime | None]] = []

    def fetch_market_data(self, tickers: list[str], since: datetime | None) -> list[MarketQuote]:
        self.calls.append((tickers, since))
        if self.error:
            raise self.error
        return self.quotes


def seed_asset(session_factory, *, price: Decimal | None = Decimal("100")) -> None:
    with session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.add(Asset(id="sap", user_id=1, name="SAP", ticker="SAP", exchange="XETRA", asset_type="Stock", status="Owned", price=price, currency="EUR", change_percent=Decimal("1"), as_of=datetime(2026, 10, 20, 9, tzinfo=UTC), industries=[]))


def test_refresh_updates_newer_quotes_and_passes_watermark(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider([MarketQuote("SAP", Decimal("110.25"), "EUR", Decimal("10.25"), datetime(2026, 10, 21, 9, tzinfo=UTC))])
    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        asset = session.get(Asset, "sap")
        assert asset.price == Decimal("110.250000")
        assert asset.change_percent == Decimal("10.250000")
        assert session.get(RefreshState, 1).last_refreshed_at is not None
    assert provider.calls == [(["SAP"], None)]


def test_refresh_reuses_values_when_provider_returns_no_newer_quote(session_factory):
    seed_asset(session_factory)
    with session_factory.begin() as session:
        session.add(RefreshState(user_id=1, last_refreshed_at=datetime(2026, 10, 21, 9)))
    provider = FakeMarketProvider([MarketQuote("SAP", Decimal("90"), "EUR", Decimal("-10"), datetime(2026, 10, 20, 9, tzinfo=UTC))])
    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("100.000000")
    assert provider.calls[0][1] == datetime(2026, 10, 21, 9)


def test_refresh_preserves_values_when_provider_fails(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider(error=TimeoutError("offline"))
    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 502
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("100.000000")
        assert session.get(RefreshState, 1).status == "unavailable"
    dashboard = build_client(session_factory, provider).get("/api/dashboard").json()
    asset = dashboard["assets"][0]
    assert asset["price"] == 100
    assert asset["asOf"] == "2026-10-20T09:00:00Z"
    assert asset["priceStatus"] == "stale"


def test_weekend_first_refresh_persists_last_available_quote_as_of_observation(session_factory):
    with session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.add(Asset(id="sap", user_id=1, name="SAP", ticker="SAP", exchange="XETRA", asset_type="Stock", status="Owned", price=None, currency=None, change_percent=None, as_of=None, industries=[]))
    friday_quote = MarketQuote("SAP", Decimal("105.50"), "EUR", Decimal("5.5"), datetime(2026, 10, 23, tzinfo=UTC))
    provider = FakeMarketProvider([friday_quote])

    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    asset = build_client(session_factory, provider).get("/api/dashboard").json()["assets"][0]
    assert asset["price"] == 105.5
    assert asset["changePercent"] == 5.5
    assert asset["asOf"] == "2026-10-23T00:00:00Z"
    assert asset["priceStatus"] == "current"


def test_incomplete_provider_result_is_unavailable_and_does_not_write(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider()
    provider.fetch_market_data = lambda tickers, since: MarketDataResult([], ["SAP"])  # type: ignore[method-assign]
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 502
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("100.000000")
        assert session.get(RefreshState, 1).status == "unavailable"


def test_omitted_symbol_in_list_result_is_unavailable(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider([MarketQuote("OTHER", Decimal("4"), "EUR", Decimal("1"), datetime(2026, 10, 21, 10, tzinfo=UTC))])
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 502
    with session_factory() as session:
        state = session.get(RefreshState, 1)
        assert state.status == "unavailable"
        assert state.unavailable_tickers == ["SAP"]


def test_no_newer_repeat_does_not_advance_watermark(session_factory):
    seed_asset(session_factory)
    watermark = datetime(2026, 10, 21, 9)
    with session_factory.begin() as session:
        session.add(RefreshState(user_id=1, last_refreshed_at=watermark))
    response = build_client(session_factory, FakeMarketProvider([])).post("/api/refresh")
    assert response.status_code == 200
    with session_factory() as session:
        assert session.get(RefreshState, 1).last_refreshed_at == watermark


def test_watermark_uses_latest_successful_quote_time(session_factory):
    seed_asset(session_factory)
    quote_time = datetime(2026, 10, 21, 12, tzinfo=UTC)
    provider = FakeMarketProvider([MarketQuote("SAP", Decimal("110"), "EUR", Decimal("10"), quote_time)])
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 200
    assert response.json()["lastRefreshedAt"] == "2026-10-21T12:00:00Z"
    with session_factory() as session:
        assert session.get(RefreshState, 1).last_refreshed_at == quote_time.replace(tzinfo=None)


class FakeNewsProvider(FakeMarketProvider):
    def __init__(self, articles: list[NewsArticle] | None = None, context: list[NewsArticle] | None = None, *, context_error: Exception | None = None):
        super().__init__([MarketQuote("SAP", Decimal("101"), "EUR", Decimal("1"), datetime(2026, 10, 22, 9, tzinfo=UTC))])
        self.articles = articles or []
        self.context = context or []
        self.context_error = context_error
        self.context_calls = 0
        self.news_calls: list[tuple[list[str], datetime | None, list[str] | None]] = []

    def fetch_news(self, tickers, since, industries=None):
        self.news_calls.append((list(tickers), since, list(industries) if industries is not None else None))
        return self.articles

    def fetch_market_context(self, since, tickers=None):
        self.context_calls += 1
        if self.context_error:
            raise self.context_error
        return self.context


def news_article(headline: str, url: str, *, identifiers: list[str] | None = None, industries: list[str] | None = None) -> NewsArticle:
    return NewsArticle(headline, "Market Wire", datetime(2026, 10, 22, 8, tzinfo=UTC), url, identifiers or [], snippet="Source supplied context.", industry_identifiers=industries or [])


def test_market_context_matches_explicit_macro_events_and_omits_irrelevant_items(session_factory):
    seed_asset(session_factory)
    provider = FakeNewsProvider(context=[
        news_article("Central bank holds interest rates steady", "https://news.test/rates"),
        news_article("Celebrity launches a new product line", "https://news.test/celebrity"),
    ])

    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        articles = list(session.query(Article).filter(Article.relevance != "Unclassified"))
        assert [(article.headline, article.relevance, article.assets, article.industries, article.snippet) for article in articles] == [
            ("Central bank holds interest rates steady", "Market context", [], [], "Source supplied context.")
        ]
        assert session.get(RefreshState, 1).market_context_checked_at is not None


def test_market_context_respects_direct_and_industry_precedence_and_deduplicates(session_factory):
    seed_asset(session_factory)
    with session_factory.begin() as session:
        session.add(Industry(id="semis", name="Semiconductors"))
        session.add(IndustryFollow(user_id=1, industry_id="semis"))
    direct = news_article("Inflation report mentions SAP", "https://news.test/direct", identifiers=["SAP"])
    industry = news_article("Export controls affect semiconductors", "https://news.test/industry", industries=["Semiconductors"])
    provider = FakeNewsProvider(articles=[direct, industry], context=[direct, industry, news_article("Inflation cools", "https://news.test/macro?utm_source=test")])

    client = build_client(session_factory, provider)
    assert client.post("/api/refresh").status_code == 200
    assert client.post("/api/refresh").status_code == 200
    with session_factory() as session:
        rows = {article.url: article for article in session.query(Article)}
        assert len(rows) == 3
        assert rows["https://news.test/direct"].relevance == "Direct asset news"
        assert rows["https://news.test/industry"].relevance == "Industry news"
        assert rows["https://news.test/macro"].relevance == "Market context"
        assert rows["https://news.test/macro"].assets == []
        assert rows["https://news.test/macro"].industries == []
        assert provider.context_calls == 1


def test_dashboard_returns_stored_market_context_without_provider_calls(session_factory):
    seed_asset(session_factory)
    with session_factory.begin() as session:
        session.add(Article(id="macro", user_id=1, headline="GDP growth slows", source="Market Wire", published_at=datetime(2026, 10, 22, 8, tzinfo=UTC), relevance="Market context", assets=[], industries=[], snippet=None, url="https://news.test/gdp"))
    provider = FakeNewsProvider()

    response = build_client(session_factory, provider).get("/api/dashboard")

    assert response.status_code == 200
    assert response.json()["articles"][0] == {
        "id": "macro", "headline": "GDP growth slows", "source": "Market Wire",
        "publishedAt": "2026-10-22T08:00:00Z", "relevance": "Market context",
        "assets": [], "industries": [], "snippet": None, "url": "https://news.test/gdp",
    }
    assert provider.calls == []
    assert provider.context_calls == 0


def test_market_context_provider_failure_keeps_quotes_and_marks_news_stale(session_factory):
    seed_asset(session_factory)
    provider = FakeNewsProvider(context_error=TimeoutError("offline"))

    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("101.000000")
        assert session.get(RefreshState, 1).news_status == "stale"
        assert session.query(Article).count() == 0


def test_partial_news_failure_saves_successful_results_and_keeps_existing_articles(session_factory):
    seed_asset(session_factory)
    preserved = news_article("Older inflation report", "https://news.test/older")
    with session_factory.begin() as session:
        session.add(Article(id="older", user_id=1, headline=preserved.headline, source=preserved.source, published_at=preserved.published_at, relevance="Market context", assets=[], industries=[], snippet=None, url=preserved.url))
    provider = FakeNewsProvider()
    provider.fetch_news = lambda tickers, since, industries=None: (_ for _ in ()).throw(PartialNewsProviderError("partial", [news_article("Payrolls rise", "https://news.test/jobs")]))

    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        assert {article.url for article in session.query(Article)} == {"https://news.test/older", "https://news.test/jobs"}
        assert session.get(RefreshState, 1).news_status == "stale"


def test_new_asset_and_industry_bypass_advanced_news_checkpoint(session_factory):
    seed_asset(session_factory)
    new_asset_article = news_article("ASML expands EUV capacity", "https://news.test/asml", identifiers=["ASML"])
    new_industry_article = news_article("Semiconductors see stronger order book", "https://news.test/semis", industries=["Semiconductors"])
    provider = FakeNewsProvider()
    provider.quotes = [
        MarketQuote(ticker, Decimal("100"), "EUR", Decimal("0"), datetime(2026, 10, 22, 9, tzinfo=UTC))
        for ticker in ("SAP", "ASML")
    ]
    client = build_client(session_factory, provider)

    # A successful empty response is still a real checkpoint, not a silent failure.
    assert client.post("/api/refresh").status_code == 200
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["newsStatus"] == "current"
    assert dashboard["articles"] == []
    with session_factory() as session:
        checkpoint = session.get(RefreshState, 1).news_checked_at
        assert checkpoint is not None

    with session_factory.begin() as session:
        session.add(Asset(id="asml", user_id=1, name="ASML", ticker="ASML", exchange="Euronext Amsterdam", asset_type="Stock", status="Interested", price=None, currency=None, change_percent=None, as_of=None, industries=["semiconductors"]))
        session.add(Industry(id="semiconductors", name="Semiconductors"))
        session.add(IndustryFollow(user_id=1, industry_id="semiconductors"))
    provider.articles = [new_asset_article, new_industry_article]

    assert client.post("/api/refresh").status_code == 200

    with session_factory() as session:
        state = session.get(RefreshState, 1)
        rows = {article.url: article for article in session.query(Article)}
        assert rows["https://news.test/asml"].assets == ["ASML"]
        assert rows["https://news.test/semis"].industries == ["semiconductors"]
        assert state.news_checked_at >= checkpoint
        assert state.news_asset_tickers == ["ASML", "SAP"]
        assert state.news_industry_ids == ["semiconductors"]
    dashboard = client.get("/api/dashboard").json()
    assert {article["url"] for article in dashboard["articles"]} == {"https://news.test/asml", "https://news.test/semis"}
    assert {article["relevance"] for article in dashboard["articles"]} == {"Direct asset news", "Industry news"}
    # The second fetch was deliberately widened to cover newly added targets.
    assert provider.news_calls[0][1] is None
    assert provider.news_calls[1][1] is None


def test_news_provider_error_marks_news_stale_and_does_not_advance_target_snapshot(session_factory):
    seed_asset(session_factory)
    provider = FakeNewsProvider()
    provider.fetch_news = lambda tickers, since, industries=None: (_ for _ in ()).throw(TimeoutError("offline"))

    assert build_client(session_factory, provider).post("/api/refresh").status_code == 200

    with session_factory() as session:
        state = session.get(RefreshState, 1)
        assert state.news_status == "stale"
        assert state.news_checked_at is None
        assert state.news_asset_tickers == []
