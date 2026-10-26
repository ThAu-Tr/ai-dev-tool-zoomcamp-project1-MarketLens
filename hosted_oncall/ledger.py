"""SQLite incident ledger compatible with a SQLite-backed Durable Object."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable


class SQLiteIncidentLedger:
    """Persist one action boundary and a redacted append-only audit per incident."""

    def __init__(self, sql, *, now: Callable[[], float] = time.time) -> None:
        self.sql = sql
        self.now = now
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS incidents ("
            "incident_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, starts_at TEXT NOT NULL, "
            "status TEXT NOT NULL, updated_at INTEGER NOT NULL)"
        )
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS incident_audit ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, incident_key TEXT NOT NULL, "
            "status TEXT NOT NULL, reason TEXT NOT NULL, created_at INTEGER NOT NULL)"
        )

    @staticmethod
    def incident_key(event: dict[str, Any]) -> str:
        raw = f"{event['fingerprint']}\n{event['startsAt']}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _one(self, query: str, *values):
        cursor = self.sql.exec(query, *values)
        return next(iter(cursor), None)

    @staticmethod
    def _value(row, name: str):
        if isinstance(row, dict) or (hasattr(row, "keys") and name in row.keys()):
            return row[name]
        return getattr(row, name)

    def _audit(self, key: str, status: str, reason: str) -> None:
        self.sql.exec(
            "INSERT INTO incident_audit (incident_key, status, reason, created_at) VALUES (?, ?, ?, ?)",
            key, status, reason, int(self.now()),
        )

    def submit(self, event: dict[str, Any]) -> str:
        key = self.incident_key(event)
        prior = self._one("SELECT status FROM incidents WHERE incident_key = ?", key)
        now = int(self.now())
        if event["status"] == "firing":
            if prior is None:
                self.sql.exec(
                    "INSERT INTO incidents (incident_key, fingerprint, starts_at, status, updated_at) "
                    "VALUES (?, ?, ?, 'pending', ?)", key, event["fingerprint"], event["startsAt"], now,
                )
                self._audit(key, "received", "approved_firing_alert")
                return "queued"
            self._audit(key, "duplicate", "repeated_firing_alert")
            return "duplicate"

        if prior is not None and self._value(prior, "status") in {"recovered", "no_action"}:
            self.sql.exec("UPDATE incidents SET status = 'resolved_pending', updated_at = ? WHERE incident_key = ?", now, key)
            self._audit(key, "resolution_pending", "grafana_resolved")
            return "queued"
        self._audit(key, "escalated", "unverified_resolution")
        return "unverified_resolution"

    def claim_next(self) -> dict[str, str] | None:
        row = self._one(
            "SELECT incident_key, fingerprint, starts_at, status FROM incidents "
            "WHERE status IN ('pending', 'resolved_pending') ORDER BY updated_at LIMIT 1"
        )
        if row is None:
            return None
        values = {name: str(self._value(row, name)) for name in ("incident_key", "fingerprint", "starts_at", "status")}
        key, previous = values["incident_key"], values["status"]
        claimed = "preflight" if previous == "pending" else "resolving"
        self.sql.exec("UPDATE incidents SET status = ?, updated_at = ? WHERE incident_key = ? AND status = ?", claimed, int(self.now()), key, previous)
        self._audit(key, claimed, "durable_work_claimed")
        values["status"] = claimed
        return values

    def transition(self, key: str, status: str, reason: str) -> bool:
        if status not in {"attempted", "recovered", "resolved", "escalated", "no_action"}:
            return False
        current = self._one("SELECT status FROM incidents WHERE incident_key = ?", key)
        if current is None:
            return False
        current_status = self._value(current, "status")
        allowed = {
            "preflight": {"attempted", "escalated", "no_action"},
            "attempted": {"recovered", "escalated"},
            "resolving": {"resolved", "escalated"},
        }
        if status not in allowed.get(current_status, set()):
            return False
        self.sql.exec("UPDATE incidents SET status = ?, updated_at = ? WHERE incident_key = ?", status, int(self.now()), key)
        self._audit(key, status, reason)
        return True

    def fail_interrupted_work(self) -> int:
        """Fail closed after a DO alarm is retried following an interrupted action."""
        cursor = self.sql.exec("SELECT incident_key, status FROM incidents WHERE status IN ('preflight', 'attempted', 'resolving')")
        interrupted = list(cursor)
        for row in interrupted:
            key = str(self._value(row, "incident_key"))
            status = str(self._value(row, "status"))
            final_reason = "restart_outcome_unknown" if status == "attempted" else "processing_interrupted"
            final_status = "escalated"
            self.sql.exec("UPDATE incidents SET status = ?, updated_at = ? WHERE incident_key = ?", final_status, int(self.now()), key)
            self._audit(key, final_status, final_reason)
        return len(interrupted)

    def audit(self, key: str) -> list[dict[str, Any]]:
        cursor = self.sql.exec(
            "SELECT status, reason, created_at FROM incident_audit WHERE incident_key = ? ORDER BY id", key
        )
        return [
            {"status": str(self._value(row, "status")), "reason": str(self._value(row, "reason")),
             "createdAt": int(self._value(row, "created_at"))}
            for row in cursor
        ]
