from __future__ import annotations

from datetime import UTC, datetime

from app.providers import MarketDataResult, ProviderGateway
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
            return RefreshResponse(lastRefreshedAt=_as_utc(since))
        refreshed_at = max(_as_utc(quote.as_of) for quote in newer)
        self.repository.apply_quotes(user.id, newer, refreshed_at)
        self.repository.session.commit()
        return RefreshResponse(lastRefreshedAt=refreshed_at)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
