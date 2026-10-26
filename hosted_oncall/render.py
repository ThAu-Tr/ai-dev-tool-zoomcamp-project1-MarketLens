"""Fixed-target Render API and MarketLens health adapter."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from urllib.parse import urlencode, urlsplit

API_ROOT = "https://api.render.com/v1"
IN_PROGRESS_DEPLOY_STATES = {
    "created", "queued", "build_in_progress", "update_in_progress", "pre_deploy_in_progress"
}
APPROVED_DASHBOARD_HOST = "marketlens-dtc.onrender.com"


class RenderRecoveryAdapter:
    """Use only public health GETs and the configured service restart endpoint."""

    def __init__(
        self,
        *,
        request: Callable[..., Awaitable[tuple[int, bytes]]],
        api_key: str,
        service_id: str,
        dashboard_url: str,
        wait: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if re.fullmatch(r"srv-[A-Za-z0-9]+", service_id) is None:
            raise ValueError("invalid_render_service_id")
        parsed_dashboard = urlsplit(dashboard_url)
        if (
            not api_key
            or parsed_dashboard.scheme != "https"
            or parsed_dashboard.hostname != APPROVED_DASHBOARD_HOST
            or parsed_dashboard.path != "/api/dashboard"
            or parsed_dashboard.username is not None
            or parsed_dashboard.password is not None
            or parsed_dashboard.query
            or parsed_dashboard.fragment
        ):
            raise ValueError("invalid_recovery_configuration")
        self._request = request
        self._api_key = api_key
        self._service_id = service_id
        self._dashboard_url = dashboard_url
        self._wait = wait

    async def _json_request(self, method: str, url: str, *, api: bool = False) -> tuple[int, Any]:
        headers = {"accept": "application/json"}
        if api:
            headers["authorization"] = f"Bearer {self._api_key}"
        status, body = await self._request(method, url, headers=headers, timeout=10)
        try:
            return status, json.loads(body) if body else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return status, None

    async def dashboard_healthy(self) -> bool | None:
        try:
            status, body = await self._json_request("GET", self._dashboard_url)
        except Exception:
            return None
        if status >= 500:
            return False
        if status != 200:
            return None
        if not isinstance(body, dict) or not {"assets", "articles", "summaries", "lastRefreshedAt", "newsStatus", "aiStatus"}.issubset(body):
            return None
        if not all(isinstance(body[key], list) for key in ("assets", "articles", "summaries")):
            return None
        return True

    async def database_ready(self) -> int | None:
        try:
            status, _ = await self._json_request("GET", self._dashboard_url.removesuffix("/api/dashboard") + "/health/ready")
            return status
        except Exception:
            return None

    @staticmethod
    def _created_at(item: dict[str, Any]) -> float:
        created = item.get("createdAt")
        if not isinstance(created, str):
            return 0.0
        try:
            parsed = datetime.fromisoformat(created.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
        except ValueError:
            return 0.0

    async def render_preflight(self) -> str:
        service_url = f"{API_ROOT}/services/{self._service_id}"
        deploy_url = f"{service_url}/deploys?{urlencode({'limit': 20})}"
        try:
            service_status, service = await self._json_request("GET", service_url, api=True)
            deploy_status, deploy_page = await self._json_request("GET", deploy_url, api=True)
        except Exception:
            return "render_api_unavailable"
        if service_status != 200 or deploy_status != 200 or not isinstance(service, dict) or not isinstance(deploy_page, list):
            return "render_api_unavailable"
        if service.get("id") != self._service_id or service.get("type") != "web_service":
            return "render_target_mismatch"
        details = service.get("serviceDetails")
        service_url = details.get("url") if isinstance(details, dict) else None
        if not isinstance(service_url, str) or urlsplit(service_url).hostname != APPROVED_DASHBOARD_HOST:
            return "render_target_mismatch"
        if service.get("suspended") != "not_suspended":
            return "render_service_suspended"

        deploys = [item.get("deploy") for item in deploy_page if isinstance(item, dict) and isinstance(item.get("deploy"), dict)]
        if not deploys:
            return "render_deploy_state_unknown"
        latest = max(deploys, key=self._created_at)
        deploy_state = latest.get("status")
        if deploy_state in IN_PROGRESS_DEPLOY_STATES:
            return "deployment_in_progress"
        if deploy_state != "live":
            return "render_deploy_state_unknown"
        return "ready"

    async def restart_service(self) -> bool:
        # The alert payload cannot select the service or operation.
        # Recheck the live service/deploy boundary immediately before POST too.
        if await self.render_preflight() != "ready":
            return False
        url = f"{API_ROOT}/services/{self._service_id}/restart"
        try:
            status, _ = await self._request(
                "POST", url,
                headers={"accept": "application/json", "authorization": f"Bearer {self._api_key}"},
                timeout=10,
            )
        except Exception:
            return False
        return status == 200

    async def wait(self, seconds: float) -> None:
        await self._wait(seconds)
