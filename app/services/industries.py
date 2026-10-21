from __future__ import annotations

from app.repositories.industries import IndustryRepository
from app.repositories.catalogue import AssetCatalogueRepository
from app.schemas import IndustryResponse


class IndustryService:
    def __init__(self, repository: IndustryRepository, catalogue: AssetCatalogueRepository | None = None) -> None:
        self.repository = repository
        self.catalogue = catalogue or AssetCatalogueRepository()

    def list(self) -> list[IndustryResponse]:
        user = self._demo_user()
        rows = self.repository.industries_with_follow_state(user.id)
        industry_ids = {industry.name.casefold(): industry.id for industry, _ in rows}
        supported_names = {str(entry_name).casefold(): str(entry_name) for entry in self.catalogue.entries() for entry_name in entry.get("industries", [])}
        supporting: dict[str, list[str]] = {}
        for asset in self.repository.watchlist_assets(user.id):
            if asset.asset_type not in {"Stock", "ETF"}:
                continue
            tags = list(asset.industries or [])
            # ETF metadata is deterministic and local to the supported catalogue.
            # Merge it with persisted tags so a stale/incomplete row cannot hide
            # a supported theme, while never inventing holdings or classifications.
            if asset.asset_type == "ETF":
                metadata_tags = next((list(entry.get("industries", [])) for entry in self.catalogue.entries()
                                      if str(entry.get("ticker", "")).casefold() == asset.ticker.casefold()
                                      and entry.get("type") == "ETF"), [])
                tags.extend(tag for tag in metadata_tags if tag not in tags)
            for tag in tags:
                canonical = supported_names.get(str(tag).casefold())
                industry_id = industry_ids.get(str(tag).casefold())
                if canonical is not None and industry_id is not None:
                    supporting.setdefault(industry_id, []).append(asset.ticker)
        followed_ids = {industry.id for industry, followed in rows if followed}
        return [IndustryResponse(id=industry.id, name=industry.name, followed=followed,
                                 suggested=industry.id not in followed_ids and industry.id in supporting,
                                 assets=sorted(set(supporting.get(industry.id, []))))
                for industry, followed in rows]

    def set_followed(self, industry_id: str, followed: bool) -> IndustryResponse | None:
        user = self._demo_user()
        industry = self.repository.industry(industry_id)
        if industry is None:
            return None
        self.repository.set_followed(user.id, industry_id, followed)
        return IndustryResponse(id=industry.id, name=industry.name, followed=followed)

    def _demo_user(self):
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        return user
