"""Minimal Kerbl Welt (backend.kerbl-iot.com) client.

Endpoints and the refresh payload follow stgarrity/kerblwelt-api (MIT).
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import BASE_URL, ENERGIZER_KEYS

_LOGGER = logging.getLogger(__name__)


class KerblAuthError(Exception):
    """Credentials or tokens rejected."""


class KerblApiError(Exception):
    """Other API or network failure."""


class KerblClient:
    """Talks to the Kerbl Welt cloud."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self.access_token = access_token
        self.refresh_token = refresh_token

    async def sign_in(self) -> None:
        data = await self._post("/auth/sign-in", {"email": self._email, "password": self._password}, auth=True)
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]

    async def _refresh(self) -> bool:
        if not (self.access_token and self.refresh_token):
            return False
        try:
            data = await self._post(
                "/auth/refresh",
                {"accessToken": self.access_token, "refreshToken": self.refresh_token},
                auth=True,
            )
        except KerblAuthError:
            return False
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        return True

    async def _post(self, path: str, payload: dict[str, Any], auth: bool = False) -> dict[str, Any]:
        try:
            async with self._session.post(f"{BASE_URL}{path}", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                text = await resp.text()
                if resp.status in (400, 401, 403) and auth:
                    raise KerblAuthError(f"{path}: HTTP {resp.status} {text[:200]}")
                raise KerblApiError(f"{path}: HTTP {resp.status} {text[:200]}")
        except aiohttp.ClientError as err:
            raise KerblApiError(f"{path}: {err}") from err

    async def _get(self, path: str, retry: bool = True) -> Any:
        if not self.access_token:
            await self.sign_in()
        try:
            async with self._session.get(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 401 and retry:
                    if not await self._refresh():
                        await self.sign_in()
                    return await self._get(path, retry=False)
                if resp.status == 401:
                    raise KerblAuthError(f"{path}: unauthorized")
                if resp.status != 200:
                    raise KerblApiError(f"{path}: HTTP {resp.status} {(await resp.text())[:200]}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise KerblApiError(f"{path}: {err}") from err

    async def get_devices_raw(self) -> dict[str, Any]:
        """Full GET /device response (all device groups)."""
        return await self._get("/device")


def find_energizers(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Pick energizer records out of the /device response."""
    for key in ENERGIZER_KEYS:
        if isinstance(raw.get(key), list):
            return raw[key]
    # Fallback: any list under a key that mentions energizer.
    for key, value in raw.items():
        if "nergizer" in key and isinstance(value, list):
            return value
    return []
