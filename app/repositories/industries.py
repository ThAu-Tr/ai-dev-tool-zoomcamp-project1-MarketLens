from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, DemoUser, Industry, IndustryFollow


class IndustryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def demo_user(self) -> DemoUser | None:
        return self.session.scalar(select(DemoUser).where(DemoUser.identifier == "demo-user"))

    def industries_with_follow_state(self, user_id: int) -> list[tuple[Industry, bool]]:
        followed_ids = select(IndustryFollow.industry_id).where(IndustryFollow.user_id == user_id)
        followed = set(self.session.scalars(followed_ids))
        return [(industry, industry.id in followed) for industry in self.session.scalars(select(Industry).order_by(Industry.name))]

    def watchlist_assets(self, user_id: int) -> list[Asset]:
        return list(self.session.scalars(select(Asset).where(Asset.user_id == user_id).order_by(Asset.ticker)))

    def industry(self, industry_id: str) -> Industry | None:
        return self.session.get(Industry, industry_id)

    def is_followed(self, user_id: int, industry_id: str) -> bool:
        return self.session.get(IndustryFollow, (user_id, industry_id)) is not None

    def set_followed(self, user_id: int, industry_id: str, followed: bool) -> None:
        record = self.session.get(IndustryFollow, (user_id, industry_id))
        if followed and record is None:
            self.session.add(IndustryFollow(user_id=user_id, industry_id=industry_id))
        elif not followed and record is not None:
            self.session.delete(record)
        self.session.commit()
