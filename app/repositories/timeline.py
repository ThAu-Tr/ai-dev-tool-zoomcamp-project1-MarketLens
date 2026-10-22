from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, DemoUser, HistoricalDay, HistoricalPrice


class TimelineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def demo_user(self) -> DemoUser | None:
        return self.session.scalar(select(DemoUser).where(DemoUser.identifier == "demo-user"))

    def assets(self, user_id: int) -> list[Asset]:
        return list(self.session.scalars(select(Asset).where(Asset.user_id == user_id).order_by(Asset.ticker)))

    def day(self, user_id: int, requested: date) -> HistoricalDay | None:
        return self.session.get(HistoricalDay, (user_id, requested))

    def prices(self, user_id: int, requested: date) -> list[HistoricalPrice]:
        return list(self.session.scalars(select(HistoricalPrice).where(
            HistoricalPrice.user_id == user_id, HistoricalPrice.market_date == requested
        ).order_by(HistoricalPrice.ticker)))

    def save(self, day: HistoricalDay, rows: list[HistoricalPrice]) -> None:
        self.session.add(day)
        self.session.add_all(rows)
        self.session.commit()
