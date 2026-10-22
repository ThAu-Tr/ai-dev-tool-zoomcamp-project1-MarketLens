from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest

from app.adapters.marketaux import MarketauxProvider


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_marketaux_normalizes_metadata_limits_and_maps_symbols_and_industries(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({"data": [
            {"uuid": "article-1", "title": "SAP quarterly update", "source": "Example News", "published_at": "2026-10-21T10:30:00Z", "url": "https://news.example/1", "snippet": "Supplied summary.", "entities": [{"symbol": "SAP", "name": "SAP SE", "type": "equity"}, {"name": "Enterprise software", "type": "industry"}]},
            {"id": "article-2", "headline": "ASML outlook", "source": "Wire", "published_at": "2026-10-21T11:00:00+00:00", "url": "https://news.example/2", "entities": [{"symbol": "ASML", "type": "equity"}]},
            {"title": "third", "source": "Wire", "published_at": "2026-10-21T12:00:00Z", "url": "https://news.example/3"},
            {"title": "fourth is trimmed", "source": "Wire", "published_at": "2026-10-21T13:00:00Z", "url": "https://news.example/4"},
            {"title": "malformed date", "source": "Wire", "published_at": "yesterday", "url": "https://news.example/5"},
        ]})

    monkeypatch.setattr("app.adapters.marketaux.urlopen", fake_urlopen)
    provider = MarketauxProvider(api_key="secret", user_agent="TestClient/1.0")
    since = datetime(2026, 10, 20, 9, tzinfo=UTC)
    articles = provider.fetch_news(["sap", "SAP", "ASML"], since)

    assert len(articles) == 3
    assert articles[0].headline == "SAP quarterly update"
    assert articles[0].published_at == datetime(2026, 10, 21, 10, 30, tzinfo=UTC)
    assert articles[0].identifiers == ["SAP"]
    assert articles[0].industry_identifiers == ["Enterprise software"]
    assert articles[0].source_identity == "article-1"
    assert articles[0].snippet == "Supplied summary."
    request = captured["request"]
    params = parse_qs(urlparse(request.full_url).query)
    assert params["symbols"] == ["SAP,ASML"]
    assert params["limit"] == ["3"]
    assert params["published_after"] == ["2026-10-20T09:00:00Z"]
    assert request.get_header("User-agent") == "TestClient/1.0"


def test_marketaux_uses_entity_symbols_only_for_requested_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.marketaux.urlopen", lambda *args, **kwargs: FakeResponse({"data": [
        {"title": "Combined update", "source": "Wire", "published_at": "2026-10-21T10:00:00Z", "url": "https://news.example/multi", "entities": [{"symbol": "SAP"}, {"symbol": "ASML"}, {"symbol": "NVDA"}]},
    ]}))
    article = MarketauxProvider(api_key="key").fetch_news(["SAP", "ASML"], None)[0]
    assert article.identifiers == ["SAP", "ASML"]


def test_marketaux_skips_request_without_credentials_or_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise AssertionError("request should not be made")

    monkeypatch.setattr("app.adapters.marketaux.urlopen", fail)
    assert MarketauxProvider(api_key=None).fetch_news(["SAP"], None) == []
    assert MarketauxProvider(api_key="key").fetch_news([], None) == []


def test_marketaux_raises_for_invalid_response_and_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.marketaux.urlopen", lambda *args, **kwargs: FakeResponse({"data": "invalid"}))
    with pytest.raises(ValueError, match="invalid news response"):
        MarketauxProvider(api_key="key").fetch_news(["SAP"], None)

    def fail(*args, **kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr("app.adapters.marketaux.urlopen", fail)
    with pytest.raises(TimeoutError):
        MarketauxProvider(api_key="key").fetch_news(["SAP"], None)


def test_marketaux_empty_page_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def empty(*args, **kwargs):
        nonlocal calls
        calls += 1
        return FakeResponse({"data": []})

    monkeypatch.setattr("app.adapters.marketaux.urlopen", empty)
    assert MarketauxProvider(api_key="key").fetch_news(["SAP"], None) == []
    assert calls == 1
