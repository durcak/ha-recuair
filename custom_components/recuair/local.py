"""Lokálne webové rozhranie jednotky Recuair (napr. DC40).

Jednotka nemá API – hodnoty sa čítajú z HTML stránok `/` a `/setting`
a príkazy sa posielajú rovnako ako z jej webu (POST /setting).
Parsovanie nezávisí od jazyka rozhrania (CZ/EN/DE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import html
import re

import aiohttp

_TIMEOUT = aiohttp.ClientTimeout(total=10)
_NUM = r"(-?\d+(?:[.,]\d+)?)"

_MODE_TEXT = {"AUTO": "auto", "HOLIDAY": "holiday", "BYPASS": "bypass", "OFF": "off", "VYP": "off", "AUS": "off"}


class RecuairError(Exception):
    """Chyba komunikácie s jednotkou."""


class RecuairConnectionError(RecuairError):
    """Jednotka je nedostupná."""


@dataclass
class RecuairState:
    """Aktuálny stav jednotky."""

    name: str | None = None
    room_temperature: float | None = None
    humidity: float | None = None
    outside_temperature: float | None = None
    mode: str | None = None
    co2: int | None = None
    filter_used: int | None = None
    ventilation: int | None = None
    light_intensity: int | None = None
    light_rgb: tuple[int, int, int] | None = None
    firmware: str | None = None
    last_update: datetime | None = field(default=None, compare=False)


def _num(value: str) -> float:
    return float(value.replace(",", "."))


def parse_state(main: str, setting: str = "") -> RecuairState:
    """Vyparsuje stav zo stránok `/` a `/setting`. Heslo Wi-Fi sa nikdy nečíta."""
    state = RecuairState()

    if m := re.search(r'name="deviceName"\s+value="([^"]*)"', main) or re.search(
        r'name="deviceName"\s+value="([^"]*)"', setting
    ):
        state.name = html.unescape(m.group(1)).strip() or None

    if m := re.search(_NUM + r"\s*°C\s*/\s*" + _NUM + r"\s*%", main):
        state.room_temperature = _num(m.group(1))
        state.humidity = _num(m.group(2))
    if m := re.search(r'logo_termo_2"\s*>\s*</i>\s*' + _NUM + r"\s*°C", main):
        state.outside_temperature = _num(m.group(1))

    if m := re.search(r"<b[^>]*>\s*(\d+)\s*ppm\s*</b>", main):
        state.co2 = int(m.group(1))

    # Pruhy: vnútorný div udáva zvyšok, hodnota je 100 − šírka (filter, potom intenzita vetrania).
    start = main.find("showModal('filterModal')")
    if start >= 0:
        widths = re.findall(r'filterBox"[^>]*>\s*<div style="width:\s*(\d+)\s*%', main[start:])
        if len(widths) >= 1:
            state.filter_used = 100 - int(widths[0])
        if len(widths) >= 2:
            state.ventilation = 100 - int(widths[1])

    # Režim: aktívne tlačidlo na /setting, inak text na hlavnej stránke.
    text_mode = None
    if m := re.search(r"showModal\('regimeModal'\).*?<span class=\"bigText\">\s*([^<]+?)\s*</span>", main, re.S):
        raw = m.group(1).strip().upper()
        text_mode = _MODE_TEXT.get(raw, raw.lower())
    if text_mode == "off":
        state.mode = "off"
    elif m := re.search(r'class="active"\s+onclick="postForm\(\s*\{\s*mode\s*:\s*\'([a-z0-9]+)\'', setting):
        state.mode = m.group(1)
    else:
        state.mode = text_mode

    if m := re.search(r'name="intensity"[^>]*\bvalue="(\d+)"', setting or main):
        state.light_intensity = int(m.group(1))
    if m := re.search(
        r'class="active"\s+onclick="postForm\(\s*\{\s*r:\s*(\d+),\s*g:\s*(\d+),\s*b:\s*(\d+)', setting
    ):
        state.light_rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    if m := re.search(r"fw:([\w.\-]+)", main):
        state.firmware = m.group(1)
    return state


class RecuairLocal:
    """Komunikácia s jednotkou v lokálnej sieti."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = host.strip().removeprefix("http://").removeprefix("https://").rstrip("/")

    @property
    def url(self) -> str:
        return f"http://{self.host}"

    async def _get(self, path: str) -> str:
        try:
            async with self._session.get(self.url + path, timeout=_TIMEOUT) as response:
                response.raise_for_status()
                return await response.text(errors="replace")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RecuairConnectionError(f"Jednotka {self.host} je nedostupná: {err}") from err

    async def fetch(self) -> RecuairState:
        """Načíta aktuálny stav jednotky."""
        main = await self._get("/")
        if 'name="deviceName"' not in main and "Recuair" not in main:
            raise RecuairError(f"Na adrese {self.host} nie je jednotka Recuair")
        setting = await self._get("/setting")
        return parse_state(main, setting)

    async def _post(self, data: dict[str, str | int]) -> None:
        try:
            async with self._session.post(
                self.url + "/setting", data={k: str(v) for k, v in data.items()}, timeout=_TIMEOUT
            ) as response:
                response.raise_for_status()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RecuairConnectionError(f"Príkaz pre {self.host} zlyhal: {err}") from err

    async def set_mode(self, mode: str) -> None:
        """Nastaví režim: auto, 1–4, holiday, bypass alebo off."""
        await self._post({"mode": mode})

    async def set_light(self, rgb: tuple[int, int, int], intensity: int) -> None:
        """Nastaví farbu a intenzitu (0–5) náladového osvetlenia."""
        await self._post({"r": rgb[0], "g": rgb[1], "b": rgb[2], "intensity": intensity})
