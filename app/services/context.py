"""Two bounded AI selections over stored evidence, only after manual refresh.

The model chooses links, never dashboard prose. Only typed persisted movement and
report-category facts are rendered; untrusted article prose never enters summaries.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit

from app.repositories.context import ContextRepository

CATEGORIES = {"Direct asset news", "Industry news", "Market context", "Not Relevant"}
INDUSTRY_CUES = {
    "semiconductors": ["chip", "chips", "chipmakers", "chipmaking"],
    "enterprise software": ["business software", "cloud software", "enterprise applications"],
    "ai": ["artificial intelligence", "machine learning"],
    "banking": ["banks", "bank lending", "lenders"],
    "renewable energy": ["solar", "wind power", "clean energy"],
}
MARKET_CUES = ["bond yields", "treasury yields", "equity futures", "recession", "risk sentiment",
               "central bank", "inflation", "interest rates", "tariffs", "global markets"]



def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _contains(text: str, name: str) -> bool:
    return bool(name and re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", text.casefold()))


def _quote_supported(quote: object, text: str, cues: list[str]) -> bool:
    return isinstance(quote, str) and 2 <= len(quote) <= 240 and quote.casefold() in text.casefold() and any(_contains(quote, cue) for cue in cues)


def _safe_article(article) -> bool:
    parts = urlsplit(article.url)
    return (parts.scheme in ("http", "https") and bool(parts.netloc) and not parts.username
            and bool(article.headline.strip()))


def _after_cursor(assets: list, cursor: str | None) -> list:
    """Start after the last processed asset so bounded batches visit all assets."""
    ids = [asset.id for asset in assets]
    if cursor not in ids:
        return assets
    index = ids.index(cursor) + 1
    return assets[index:] + assets[:index]


def _relevant(article, asset, followed: dict[str, str]) -> bool:
    if article.relevance == "Direct asset news":
        return asset.ticker in article.assets
    if article.relevance == "Industry news":
        return any(i in followed and (i in asset.industries or followed[i] in asset.industries) for i in article.industries)
    return article.relevance == "Market context"


class ContextService:
    def __init__(self, repository: ContextRepository, provider, now: datetime | None = None) -> None:
        self.repository = repository
        self.provider = provider
        self.now = now or datetime.now(UTC)

    def refresh(self, user_id: int) -> None:
        generate = getattr(self.provider, "generate_context", None)
        all_assets = self.repository.assets_for(user_id)
        if not all_assets:
            self.repository.set_ai_status(user_id, "no_evidence")
            return
        ordered_assets = _after_cursor(all_assets, self.repository.ai_asset_cursor(user_id))
        asset_batch = ordered_assets[:5]
        since = self.now - timedelta(days=3)
        industries = self.repository.followed_industries(user_id)[:8]
        ambiguous = [row for row in self.repository.articles_for(user_id, since, ambiguous=True)
                     if _utc(row.published_at) <= self.now]
        pending = self._pending(user_id, ordered_assets, industries, since)[:5]
        if not ambiguous and not pending:
            has_summary = any(self.repository.summaries_for(user_id, asset.id) for asset in all_assets)
            self.repository.set_ai_status(user_id, "current" if has_summary else "no_evidence")
            return
        if not callable(generate) or getattr(self.provider, "ai_available", True) is False:
            self.repository.set_ai_status(user_id, "unavailable")
            return
        if not self.repository.claim_budget(user_id, self.now):
            self.repository.set_ai_status(user_id, "cooldown")
            return
        status = "failed"
        cursor = pending[-1][0].id if pending else asset_batch[-1].id
        if ambiguous:
            facts = {"assets": [{"id": a.ticker, "name": a.name} for a in asset_batch],
                     "industries": [{"id": i.id, "name": i.name} for i in industries],
                     "articles": [self._article_fact(a) for a in ambiguous]}
            try:
                result = generate("classify", facts)
                self._classify(result, ambiguous, asset_batch, industries)
                self.repository.session.commit()
                status = "current"
            except Exception:
                self.repository.session.rollback()
        pending = self._pending(user_id, ordered_assets, industries, since)[:5]
        if not pending:
            # A valid run that classifies every candidate as irrelevant (or
            # cannot validate the links) correctly produces no card.
            self.repository.set_ai_status(user_id, "no_evidence" if status != "failed" else "failed", cursor)
            return
        cursor = pending[-1][0].id
        facts = {"assets": [{"id": a.id, "ticker": a.ticker, "price": str(a.price), "currency": a.currency,
                             "change_percent": str(a.change_percent), "as_of": _utc(a.as_of).isoformat(),
                             "articles": [self._article_fact(row) for row in rows]}
                            for a, rows, fingerprint in pending]}
        try:
            result = generate("summarize", facts)
            saved = self._save_summaries(user_id, result, pending)
            self.repository.session.commit()
            status = "current" if saved else "failed"
        except Exception:
            self.repository.session.rollback()
            status = "failed"
        self.repository.set_ai_status(user_id, status, cursor)

    @staticmethod
    def _article_fact(article) -> dict:
        return {"id": article.id, "headline": article.headline[:500], "snippet": (article.snippet or "")[:500],
                "relevance": article.relevance, "published_at": _utc(article.published_at).isoformat()}

    def _pending(self, user_id, assets, industries, since):
        articles = [row for row in self.repository.articles_for(user_id, since)
                    if _utc(row.published_at) <= self.now and _safe_article(row)]
        followed = {industry.id: industry.name for industry in industries}
        pending = []
        for asset in assets:
            if (asset.price is None or asset.change_percent is None or asset.as_of is None
                    or not asset.currency or not since <= _utc(asset.as_of) <= self.now):
                continue
            relevant = [row for row in articles if _relevant(row, asset, followed)][:3]
            if not relevant:
                continue
            # All supplied evidence, not just selected IDs, invalidates a stale card.
            facts = ["typed-context-v2", asset.id, str(asset.price), asset.currency, str(asset.change_percent), _utc(asset.as_of).isoformat(),
                     [(a.id, a.headline, a.snippet, a.relevance, a.assets, a.industries, a.url) for a in relevant]]
            fingerprint = "ai-" + sha256(asset.id.encode()).hexdigest()[:16] + "-" + sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()[:40]
            if not any(row.id == fingerprint for row in self.repository.summaries_for(user_id, asset.id)):
                pending.append((asset, relevant, fingerprint))
        return pending

    def _classify(self, result, articles, assets, industries):
        if not isinstance(result, dict) or set(result) != {"classifications"}:
            return
        rows = result["classifications"]
        if not isinstance(rows, list) or len(rows) > 5:
            return
        candidates = {a.id: a for a in articles}
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"article_id", "relevance", "asset_links", "industry_links", "market_evidence"}:
                continue
            article_id = row["article_id"]
            if not isinstance(article_id, str) or article_id not in candidates or article_id in seen:
                continue
            seen.add(article_id)
            article = candidates[article_id]
            if article.relevance != "Unclassified" or row["relevance"] not in CATEGORIES:
                continue
            text = f"{article.headline} {(article.snippet or '')[:500]}"
            asset_map = {a.ticker: [a.ticker, a.name] for a in assets}
            industry_map = {i.id: [i.name, *INDUSTRY_CUES.get(i.name.casefold(), [])] for i in industries}
            linked_assets = self._validated_links(row["asset_links"], text, asset_map)
            linked_industries = self._validated_links(row["industry_links"], text, industry_map)
            if linked_assets is None or linked_industries is None:
                continue
            market_quote = row["market_evidence"]
            if not isinstance(market_quote, str) or (market_quote and not _quote_supported(market_quote, text, MARKET_CUES)):
                continue
            relevance = ("Direct asset news" if linked_assets else "Industry news" if linked_industries
                         else "Market context" if market_quote else "Not Relevant")
            if row["relevance"] != relevance:
                continue
            self.repository.classify_article(article, relevance, linked_assets, [] if linked_assets else linked_industries)

    @staticmethod
    def _validated_links(links, text, available):
        if not isinstance(links, list) or len(links) > 5:
            return None
        linked = []
        for link in links:
            if (not isinstance(link, dict) or set(link) != {"id", "evidence"}
                    or not isinstance(link["id"], str) or link["id"] not in available
                    or link["id"] in linked or not _quote_supported(link["evidence"], text, available[link["id"]])):
                return None
            linked.append(link["id"])
        return sorted(linked)

    def _save_summaries(self, user_id, result, pending):
        if not isinstance(result, dict) or set(result) != {"summaries"}:
            return False
        rows = result["summaries"]
        if not isinstance(rows, list) or len(rows) > 5:
            return False
        available = {asset.id: (asset, articles, fingerprint) for asset, articles, fingerprint in pending}
        seen = set()
        saved = False
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"asset_id", "article_ids"} or not isinstance(row["asset_id"], str):
                continue
            asset_id = row["asset_id"]
            if asset_id not in available or asset_id in seen:
                continue
            seen.add(asset_id)
            asset, articles, fingerprint = available[asset_id]
            ids = row["article_ids"]
            by_id = {a.id: a for a in articles}
            if (not isinstance(ids, list) or not 1 <= len(ids) <= 2 or not all(isinstance(i, str) for i in ids)
                    or len(set(ids)) != len(ids) or any(i not in by_id for i in ids)):
                continue
            # Never quote or paraphrase untrusted source prose here. Even an
            # attributed headline can repeat advice, targets or causal claims.
            labels = {"Direct asset news": "direct asset", "Industry news": "industry", "Market context": "broader market"}
            counts = {category: sum(by_id[i].relevance == category for i in ids) for category in labels}
            reports = ", ".join(f"{count} {labels[category]} report{'s' if count != 1 else ''}"
                                for category, count in counts.items() if count)
            price = format(asset.price.normalize(), "f")
            text = (f"Possible context alongside {asset.ticker}'s {asset.change_percent:+.2f}% movement "
                    f"(stored price {price} {asset.currency}): {reports} linked below. "
                    "These reports may be relevant; they do not establish a cause of the movement.")
            if len(text) <= 600:
                self.repository.save_summary(user_id, asset.id, fingerprint, text, ids)
                saved = True
        return saved
