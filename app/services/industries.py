from __future__ import annotations

from app.repositories.industries import IndustryRepository
from app.schemas import IndustryResponse


class IndustryService:
    def __init__(self, repository: IndustryRepository) -> None:
        self.repository = repository

    def list(self) -> list[IndustryResponse]:
        user = self._demo_user()
        return [IndustryResponse(id=industry.id, name=industry.name, followed=followed) for industry, followed in self.repository.industries_with_follow_state(user.id)]

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
