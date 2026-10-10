"""Voliteľný cloud Recuair (recuair.enobis.eu) – otáčky ventilátorov, zrekuperovaná energia a ďalšie.

Cloud nemá verejné API. Prihlásenie emuluje webový portál: OAuth2 authorization
code + PKCE cez prihlasovací formulár (e-mail/meno a heslo).
"""

from __future__ import annotations

import base64
from datetime import date
import hashlib
import re
import secrets
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import aiohttp

AUTH_URL = "https://auth-recuair.enobis.eu"
API_URL = "https://recuair.enobis.eu/api"
CLIENT_ID = "recuair-client-public"
REDIRECT_URI = "https://recuair.enobis.eu/callback"
SCOPE = "openid profile"

_TIMEOUT = aiohttp.ClientTimeout(total=30)


class RecuairCloudError(Exception):
    """Chyba cloudu Recuair."""


class RecuairCloudAuthError(RecuairCloudError):
    """Nesprávne prihlasovacie údaje."""


class RecuairCloud:
    """Prihlásenie a čítanie dát z cloudu Recuair."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def login(self) -> None:
        """Prihlásenie cez webový formulár a výmena autorizačného kódu za tokeny."""
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": secrets.token_urlsafe(16),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        # Samostatná session s vlastnými cookies (JSESSIONID prihlasovacieho servera).
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(), timeout=_TIMEOUT) as auth:
            try:
                async with auth.get(f"{AUTH_URL}/oauth2/authorize", params=params) as response:
                    page = await response.text()
                csrf = re.search(r'name="_csrf"\s+value="([^"]+)"', page)
                if not csrf:
                    raise RecuairCloudError("Prihlasovacia stránka neobsahuje CSRF token")
                async with auth.post(
                    f"{AUTH_URL}/login",
                    data={"username": self._username, "password": self._password, "_csrf": csrf.group(1)},
                    allow_redirects=False,
                ) as response:
                    location = response.headers.get("Location", "")
                if not location or "error" in location:
                    raise RecuairCloudAuthError("Nesprávne prihlasovacie údaje")
                code = None
                for _ in range(6):
                    if location.startswith(REDIRECT_URI):
                        code = parse_qs(urlparse(location).query).get("code", [None])[0]
                        break
                    async with auth.get(urljoin(AUTH_URL, location), allow_redirects=False) as response:
                        location = response.headers.get("Location", "")
                    if not location:
                        break
                if not code:
                    raise RecuairCloudAuthError("Autorizačný kód sa nepodarilo získať")
                async with auth.post(
                    f"{AUTH_URL}/oauth2/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": REDIRECT_URI,
                        "client_id": CLIENT_ID,
                        "code_verifier": verifier,
                    },
                ) as response:
                    if response.status != 200:
                        raise RecuairCloudAuthError(f"Výmena kódu za token zlyhala (HTTP {response.status})")
                    tokens = await response.json()
            except aiohttp.ClientError as err:
                raise RecuairCloudError(f"Cloud Recuair je nedostupný: {err}") from err
        self._access_token = tokens.get("access_token")
        self._refresh_token = tokens.get("refresh_token")
        if not self._access_token:
            raise RecuairCloudAuthError("Odpoveď neobsahuje access token")

    async def _refresh(self) -> bool:
        if not self._refresh_token:
            return False
        try:
            async with self._session.post(
                f"{AUTH_URL}/oauth2/token",
                data={"grant_type": "refresh_token", "refresh_token": self._refresh_token, "client_id": CLIENT_ID},
                timeout=_TIMEOUT,
            ) as response:
                if response.status != 200:
                    return False
                tokens = await response.json()
        except aiohttp.ClientError:
            return False
        self._access_token = tokens.get("access_token")
        self._refresh_token = tokens.get("refresh_token", self._refresh_token)
        return bool(self._access_token)

    async def _get(self, path: str, params: dict[str, str] | None = None, *, retry: bool = True) -> Any:
        if not self._access_token:
            await self.login()
        try:
            async with self._session.get(
                f"{API_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"},
                timeout=_TIMEOUT,
            ) as response:
                status = response.status
                body = await response.json(content_type=None) if status == 200 else None
        except aiohttp.ClientError as err:
            raise RecuairCloudError(f"Cloud Recuair je nedostupný: {err}") from err
        if status == 401 and retry:
            if not await self._refresh():
                await self.login()
            return await self._get(path, params, retry=False)
        if status != 200:
            raise RecuairCloudError(f"Cloud Recuair vrátil HTTP {status} pre {path}")
        return body

    async def devices(self) -> list[dict[str, Any]]:
        """Zariadenia v účte: id, názov, sériové číslo, typ."""
        # Rovnaké parametre ako webový portál (bez `loc` server požiadavku odmieta).
        data = await self._get("/devices", {"loc": "sk_SK", "page": "0", "size": "20"})
        return [
            {
                "id": item.get("_id"),
                "name": item.get("observable.name"),
                "serial": item.get("observable.serialNumber"),
                "type": item.get("observableType.code"),
            }
            for item in (data or {}).get("content", [])
            if item.get("_id") is not None
        ]

    async def observation(self, device_id: int) -> dict[str, Any]:
        """Posledné hodnoty zariadenia (observableValue) a stav pripojenia."""
        data = await self._get(
            f"/dashboard/{device_id}",
            {"updateData": "true", "onlyObservation": "false", "dateFrom": date.today().isoformat()},
        )
        value = dict(((data or {}).get("observable") or {}).get("observableValue") or {})
        value["connected"] = (data or {}).get("connected")
        return value
