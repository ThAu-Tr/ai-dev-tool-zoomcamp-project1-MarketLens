from __future__ import annotations

from typing import Protocol


class ProviderGateway(Protocol):
    """Boundary for external market, news, and AI adapters.

    Dashboard reads deliberately receive this boundary but must never use it.
    Refresh and historical workflows will call concrete adapters in later issues.
    """

    def fetch_market_data(self) -> None: ...

    def fetch_news(self) -> None: ...

    def generate_context(self) -> None: ...
