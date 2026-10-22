from __future__ import annotations

from datetime import date
from hashlib import sha256

from app.models import HistoricalDay, HistoricalPrice
from app.providers import MarketDataResult, ProviderGateway
from app.repositories.timeline import TimelineRepository
from app.schemas import AssetResponse, TimelineDayResponse


class HistoricalProviderError(RuntimeError):
    pass


class HistoricalDateOutOfRange(LookupError):
    pass


class TimelineService:
    def __init__(self, repository: TimelineRepository, provider: ProviderGateway | None) -> None:
        self.repository = repository
        self.provider = provider

    def get_day(self, requested: date, today: date | None = None) -> TimelineDayResponse:
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        archived = self.repository.day(user.id, requested)
        if archived is not None:
            return self._response(requested, "archive", archived.market_closed, self.repository.prices(user.id, requested))
        today = today or date.today()
        if requested > today:
            raise ValueError("The requested date cannot be in the future.")
        if (today - requested).days > 30:
            raise HistoricalDateOutOfRange("This date is outside the 30-day history window and is not archived.")
        if self.provider is None or not callable(getattr(self.provider, "fetch_historical_data", None)):
            raise HistoricalProviderError("Historical market data is currently unavailable. Please try again.")
        assets = self.repository.assets(user.id)
        try:
            result = self.provider.fetch_historical_data([asset.ticker for asset in assets], requested)
        except Exception as error:
            raise HistoricalProviderError("Historical market data is currently unavailable. Please try again.") from error
        if isinstance(result, MarketDataResult):
            if result.unavailable_tickers:
                raise HistoricalProviderError("Historical market data is incomplete. No day was saved; please try again.")
            quotes, market_closed = result.quotes, result.market_closed
        else:
            quotes, market_closed = result, False
        by_ticker = {quote.ticker.upper(): quote for quote in quotes}
        day = HistoricalDay(user_id=user.id, market_date=requested, market_closed=market_closed or (not quotes))
        rows = []
        for asset in assets:
            quote = by_ticker.get(asset.ticker.upper())
            rows.append(HistoricalPrice(
                id=sha256(f"{user.id}:{requested}:{asset.id}".encode()).hexdigest(), user_id=user.id,
                market_date=requested, asset_id=asset.id, ticker=asset.ticker, name=asset.name,
                exchange=asset.exchange, asset_type=asset.asset_type, status=asset.status,
                price=quote.price if quote else None, currency=quote.currency if quote else None,
                change_percent=quote.change_percent if quote else None, as_of=quote.as_of if quote else None,
                industries=list(asset.industries or []),
            ))
        self.repository.save(day, rows)
        return self._response(requested, "newly-loaded", day.market_closed, rows)

    @staticmethod
    def _response(requested: date, source: str, market_closed: bool, rows: list[HistoricalPrice]) -> TimelineDayResponse:
        assets = [AssetResponse(id=row.asset_id, name=row.name, ticker=row.ticker, exchange=row.exchange,
            type=row.asset_type, status=row.status, price=row.price, currency=row.currency,
            changePercent=row.change_percent, asOf=row.as_of, lots=[], industries=row.industries,
            priceStatus="unavailable" if row.price is None else "current") for row in rows]
        return TimelineDayResponse(date=requested, source=source, marketClosed=market_closed,
                                  assets=assets, articles=[], summaries=[])
