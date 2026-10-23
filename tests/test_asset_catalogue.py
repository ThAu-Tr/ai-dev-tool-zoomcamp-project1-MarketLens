from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.catalogue import AssetCatalogueRepository
from app.services.catalogue import AssetCatalogueService


def test_catalogue_search_matches_name_and_ticker_case_insensitively() -> None:
    client = TestClient(create_app())

    by_ticker = client.get('/api/assets/search', params={'q': 'asml'})
    by_name = client.get('/api/assets/search', params={'q': 'CLEAN ENERGY'})

    assert by_ticker.status_code == 200
    assert by_ticker.json() == [{'name': 'ASML Holding', 'ticker': 'ASML', 'exchange': 'Euronext Amsterdam', 'type': 'Stock'}]
    assert by_name.status_code == 200
    assert by_name.json() == [{'name': 'iShares Global Clean Energy ETF', 'ticker': 'ICLN', 'exchange': 'NASDAQ', 'type': 'ETF'}]


def test_catalogue_search_returns_empty_list_for_no_match() -> None:
    response = TestClient(create_app()).get('/api/assets/search', params={'q': 'not in this catalogue'})

    assert response.status_code == 200
    assert response.json() == []


def test_catalogue_includes_apple_and_a_bounded_mix_of_stocks_etfs_and_indices() -> None:
    client = TestClient(create_app())

    apple = client.get('/api/assets/search', params={'q': 'aapl'})
    assert apple.status_code == 200
    assert apple.json() == [{'name': 'Apple Inc.', 'ticker': 'AAPL', 'exchange': 'NASDAQ', 'type': 'Stock'}]

    records = list(AssetCatalogueRepository().entries())
    assert len(records) >= 25
    assert {entry['type'] for entry in records} == {'Stock', 'ETF', 'Index'}
    assert len({(entry['ticker'].casefold(), entry['exchange'].casefold()) for entry in records}) == len(records)


def test_catalogue_service_discards_duplicate_and_malformed_records() -> None:
    class CatalogueWithInvalidEntries:
        def entries(self) -> list[dict[str, str]]:
            return [
                {'name': 'ASML Holding', 'ticker': 'ASML', 'exchange': 'Euronext Amsterdam', 'type': 'Stock'},
                {'name': 'ASML Holding duplicate', 'ticker': 'asml', 'exchange': 'euronext amsterdam', 'type': 'Stock'},
                {'name': 'Unsupported bond', 'ticker': 'BOND', 'exchange': 'XETRA', 'type': 'Bond'},
                {'name': 'Missing exchange', 'ticker': 'MISSING', 'type': 'Stock'},
            ]

    results = AssetCatalogueService(CatalogueWithInvalidEntries()).search('asml')  # type: ignore[arg-type]

    assert [result.model_dump() for result in results] == [
        {'name': 'ASML Holding', 'ticker': 'ASML', 'exchange': 'Euronext Amsterdam', 'type': 'Stock'},
    ]


def test_catalogue_search_rejects_missing_empty_and_whitespace_queries() -> None:
    client = TestClient(create_app())

    assert client.get('/api/assets/search').status_code == 422
    assert client.get('/api/assets/search', params={'q': ''}).status_code == 422
    assert client.get('/api/assets/search', params={'q': '   '}).status_code == 422
