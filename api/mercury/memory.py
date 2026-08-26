from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, cast

from sibyl_memory_client import MemoryClient, NotFoundError, SibylMemoryError


class MemoryUnavailable(RuntimeError):
    pass


class IncidentMemoryStore:
    """The only durable application store: official Sibyl Memory entities + journal."""

    def __init__(self, path: str | Path | None = None, tenant_id: str | None = None) -> None:
        resolved_path = path if path is not None else os.getenv("SIBYL_DB_PATH", "./data/mercury-memory.db")
        self.path = Path(resolved_path)
        self.tenant_id = tenant_id or os.getenv("SIBYL_TENANT_ID", "mercury")

    def _client(self) -> MemoryClient:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            return MemoryClient.local(self.path, tenant_id=self.tenant_id)
        except Exception as exc:
            raise MemoryUnavailable(f"Sibyl Memory unavailable: {exc}") from exc

    def health(self) -> dict[str, Any]:
        try:
            count = len(self._client().list_entities(category="incident", limit=10000))
            return {"status": "online", "provider": "sibyl-memory-client", "path": str(self.path), "incident_count": count}
        except MemoryUnavailable as exc:
            return {"status": "degraded", "provider": "sibyl-memory-client", "error": str(exc)}

    def next_incident_id(self) -> str:
        records = self._client().list_entities(category="incident", limit=10000)
        numbers = [int(match.group(1)) for item in records if (match := re.fullmatch(r"INC-(\d+)", str(item.get("name", ""))))]
        return f"INC-{max(numbers, default=103) + 1:03d}"

    def save(self, incident: dict[str, Any]) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], self._client().set_entity("incident", incident["incident_id"], incident, status=incident["status"]))
        except SibylMemoryError as exc:
            raise MemoryUnavailable(f"Sibyl write failed: {exc}") from exc

    def set_entity(self, category: str, name: str, body: dict[str, Any], *, status: str = "active") -> dict[str, Any]:
        """Persist non-incident coordination/proof records in the same Sibyl database."""
        try:
            return cast(dict[str, Any], self._client().set_entity(category, name, body, status=status))
        except SibylMemoryError as exc:
            raise MemoryUnavailable(f"Sibyl write failed: {exc}") from exc

    def get_entity(self, category: str, name: str) -> dict[str, Any] | None:
        try:
            return cast(dict[str, Any], self._client().get_entity(category, name))
        except NotFoundError:
            return None
        except SibylMemoryError as exc:
            raise MemoryUnavailable(f"Sibyl read failed: {exc}") from exc

    def incident_record(self, incident_id: str) -> dict[str, Any] | None:
        return self.get_entity("incident", incident_id)

    def get(self, incident_id: str) -> dict[str, Any] | None:
        try:
            return cast(dict[str, Any], self._client().get_entity("incident", incident_id)["body"])
        except NotFoundError:
            return None
        except SibylMemoryError as exc:
            raise MemoryUnavailable(f"Sibyl read failed: {exc}") from exc

    def search(self, terms: list[str], exclude_incident_id: str) -> list[dict[str, Any]]:
        client = self._client()
        found: dict[str, dict[str, Any]] = {}
        try:
            for term in terms[:16]:
                for hit in client.search_entities(term, category="incident", limit=50, prefix=True):
                    key = str(hit.get("name") or hit.get("key"))
                    body = hit.get("body")
                    if not isinstance(body, dict) or key == exclude_incident_id:
                        continue
                    if body.get("status") != "resolved" or body.get("superseded_by"):
                        continue
                    found[key] = body
            return list(found.values())
        except SibylMemoryError as exc:
            raise MemoryUnavailable(f"Sibyl search failed: {exc}") from exc

    def journal(self, *, evaluated: Any = None, acted: Any = None, forward: Any = None, extra: Any = None) -> str:
        try:
            return cast(str, self._client().write_event(evaluated=evaluated, acted=acted, forward=forward, extra=extra))
        except SibylMemoryError as exc:
            raise MemoryUnavailable(f"Sibyl journal write failed: {exc}") from exc
