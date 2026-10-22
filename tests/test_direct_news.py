from datetime import UTC, datetime
from decimal import Decimal

from app.models import Article, Asset, DemoUser, Industry, IndustryFollow, RefreshState
from app.providers import MarketQuote, NewsArticle
from tests.test_dashboard import build_client
from tests.test_refresh import session_factory  # noqa: F401 - pytest fixture


class FakeNewsProvider:
    def __init__(self, articles: list[NewsArticle], *, news_error: Exception | None = None) -> None:
        self.articles = articles
        self.news_error = news_error
        self.news_calls: list[tuple[list[str], datetime | None, list[str] | None]] = []

    def fetch_market_data(self, tickers: list[str], since: datetime | None) -> list[MarketQuote]:
        return [MarketQuote(ticker, Decimal("101"), "EUR", Decimal("1"), datetime(2026, 10, 21, 10, tzinfo=UTC)) for ticker in tickers]

    def fetch_news(self, tickers: list[str], since: datetime | None, industries: list[str] | None = None) -> list[NewsArticle]:
        self.news_calls.append((tickers, since, industries))
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
    assert provider.news_calls[1][1] > datetime(2026, 10, 21, 9)


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


def test_refresh_saves_only_followed_industry_matches_and_direct_news_takes_precedence(session_factory):
    seed_assets(session_factory)
    with session_factory.begin() as session:
        session.add_all([
            Industry(id="semi", name="Semiconductors"),
            Industry(id="software", name="Enterprise software"),
            Industry(id="energy", name="Renewable energy"),
            IndustryFollow(user_id=1, industry_id="semi"),
            IndustryFollow(user_id=1, industry_id="software"),
        ])
        # Persisted asset tags are the taxonomy evidence associated with follows.
        session.get(Asset, "sap").industries = ["Enterprise software"]
        session.get(Asset, "asml").industries = ["Semiconductors"]
    provider = FakeNewsProvider([
        news("Semiconductors and enterprise software outlook", [], url="https://news.example/multi", identity="multi"),
        news("Renewable energy outlook", [], url="https://news.example/unfollowed", identity="unfollowed"),
        news("What analysts said about the outlook", [], url="https://news.example/substring", identity="substring"),
        news("Semiconductors supplier update", ["ASML"], url="https://news.example/direct-sector", identity="direct"),
    ])

    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 200
    with session_factory() as session:
        articles = session.query(Article).order_by(Article.url).all()
        assert [(article.url, article.relevance, article.industries, article.assets) for article in articles] == [
            ("https://news.example/direct-sector", "Direct asset news", [], ["ASML"]),
            ("https://news.example/multi", "Industry news", ["semi", "software"], []),
        ]

    dashboard = build_client(session_factory).get("/api/dashboard")
    industry_article = next(article for article in dashboard.json()["articles"] if article["relevance"] == "Industry news")
    assert industry_article["industries"] == ["Semiconductors", "Enterprise software"]

    build_client(session_factory, provider).post("/api/refresh")
    with session_factory() as session:
        assert session.query(Article).count() == 2


def test_refresh_does_not_infer_industry_relevance_from_unfollowed_or_uncertain_text(session_factory):
    seed_assets(session_factory)
    with session_factory.begin() as session:
        session.add_all([Industry(id="semi", name="Semiconductors"), Industry(id="ai", name="AI")])
        session.add(IndustryFollow(user_id=1, industry_id="ai"))
    provider = FakeNewsProvider([
        news("Semiconductors outlook", [], url="https://news.example/not-followed", identity="not-followed"),
        news("A general technology update", [], url="https://news.example/uncertain", identity="uncertain"),
    ])
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 200
    with session_factory() as session:
        assert session.query(Article).count() == 0


def test_refresh_uses_explicit_marketaux_industry_metadata_for_followed_industries(session_factory):
    seed_assets(session_factory)
    with session_factory.begin() as session:
        session.add_all([Industry(id="software", name="Enterprise software"), IndustryFollow(user_id=1, industry_id="software")])
    article = NewsArticle(
        headline="Quarterly outlook", source="Wire", published_at=datetime(2026, 10, 21, 9, tzinfo=UTC),
        url="https://news.example/software", identifiers=[], industry_identifiers=["Enterprise software"],
    )
    response = build_client(session_factory, FakeNewsProvider([article])).post("/api/refresh")
    assert response.status_code == 200
    with session_factory() as session:
        saved = session.query(Article).one()
        assert saved.relevance == "Industry news"
        assert saved.industries == ["software"]


def test_refresh_passes_followed_industries_and_advances_checkpoint_for_irrelevant_results(session_factory):
    seed_assets(session_factory)
    with session_factory.begin() as session:
        session.add_all([Industry(id="software", name="Enterprise software"), IndustryFollow(user_id=1, industry_id="software")])
    irrelevant = news("Unrelated market item", [], url="https://news.example/irrelevant", identity="irrelevant")
    provider = FakeNewsProvider([irrelevant])

    assert build_client(session_factory, provider).post("/api/refresh").status_code == 200
    with session_factory() as session:
        first_checkpoint = session.get(RefreshState, 1).news_checked_at
        assert first_checkpoint is not None
        assert session.query(Article).count() == 0
    assert provider.news_calls[0][2] == ["Enterprise software"]

    assert build_client(session_factory, provider).post("/api/refresh").status_code == 200
    assert provider.news_calls[1][1] == first_checkpoint
    with session_factory() as session:
        assert session.get(RefreshState, 1).news_checked_at >= first_checkpoint
        assert session.query(Article).count() == 0


def test_marketaux_parent_industry_filter_is_not_proof_of_followed_industry_relevance(session_factory):
    seed_assets(session_factory)
    with session_factory.begin() as session:
        session.add_all([Industry(id="software", name="Enterprise software"), IndustryFollow(user_id=1, industry_id="software")])
    broad_category_only = NewsArticle(
        headline="Unrelated corporate update", source="Wire", published_at=datetime(2026, 10, 21, 9, tzinfo=UTC),
        url="https://news.example/technology", identifiers=[], industry_identifiers=["Technology"],
    )

    response = build_client(session_factory, FakeNewsProvider([broad_category_only])).post("/api/refresh")
    assert response.status_code == 200
    with session_factory() as session:
        assert session.query(Article).count() == 0
