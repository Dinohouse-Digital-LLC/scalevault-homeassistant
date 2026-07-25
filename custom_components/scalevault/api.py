"""Thin async client for the ScaleVault HTTP API.

The integration authenticates with a per-account API key generated in ScaleVault
under Account Settings → Integrations. The key is scoped (readings:write /
events:write / targets:list) on the server side; this client just carries it as a
bearer token.
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .const import API_ACTIONS, API_INGEST, API_TARGETS, API_VALIDATE, CLIENT_IDENTIFIER

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=15)


class ScaleVaultAuthError(Exception):
    """The API key was rejected (401/403)."""


class ScaleVaultConnectionError(Exception):
    """ScaleVault could not be reached, or returned an unexpected error."""


class ScaleVaultClient:
    """Minimal wrapper around the ScaleVault endpoints the integration uses."""

    def __init__(self, session: ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            # Lets ScaleVault's Settings UI show "Connected via Home Assistant
            # custom component" instead of just "connected" — the manual
            # rest_command/webhook recipe never sends this header.
            "X-ScaleVault-Client": CLIENT_IDENTIFIER,
        }

    async def async_validate(self) -> dict[str, Any]:
        """Verify the API key and return the account info it maps to.

        Raises ScaleVaultAuthError / ScaleVaultConnectionError on failure.
        """
        data = await self._request("POST", API_VALIDATE)
        return data if isinstance(data, dict) else {}

    async def async_list_targets(self) -> list[dict[str, Any]]:
        """Return the account's enclosures/animals for config-flow dropdowns."""
        data = await self._request("GET", API_TARGETS)
        return data.get("targets", []) if isinstance(data, dict) else []

    async def async_push_readings(self, readings: list[dict[str, Any]]) -> None:
        """Push a batch of climate readings to ScaleVault."""
        await self._request("POST", API_INGEST, json={"readings": readings})

    async def async_log_action(self, payload: dict[str, Any]) -> None:
        """Log a quick husbandry action (feeding, watering, ...)."""
        await self._request("POST", API_ACTIONS, json=payload)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method, url, headers=self._headers, timeout=_TIMEOUT, **kwargs
            ) as resp:
                if resp.status in (401, 403):
                    detail = await self._error_detail(resp)
                    raise ScaleVaultAuthError(detail or f"ScaleVault rejected the API key ({resp.status})")
                resp.raise_for_status()
                if resp.content_type == "application/json":
                    return await resp.json()
                return None
        except ClientResponseError as err:
            _LOGGER.debug("ScaleVault request to %s failed: %s", path, err)
            raise ScaleVaultConnectionError from err
        except (ClientError, TimeoutError) as err:
            _LOGGER.debug("ScaleVault request to %s failed: %s", path, err)
            raise ScaleVaultConnectionError from err

    @staticmethod
    async def _error_detail(resp: Any) -> str | None:
        """Best-effort extraction of the server's {"error": "..."} message, so
        callers see e.g. "This key is not scoped for 'events:write'" instead of
        a generic "rejected" message that hides the actual, actionable cause."""
        try:
            data = await resp.json()
        except Exception:  # noqa: BLE001 - malformed/non-JSON body is not fatal here
            return None
        return data.get("error") if isinstance(data, dict) else None
