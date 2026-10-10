"""Nastavenie Recuair: adresa jednotky a voliteľne účet v cloude."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .cloud import RecuairCloud, RecuairCloudAuthError, RecuairCloudError
from .const import (
    CONF_CLOUD_DEVICE_ID,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .local import RecuairConnectionError, RecuairError, RecuairLocal

_LOGGER = logging.getLogger(__name__)

SCAN_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=3600, step=5, unit_of_measurement="s", mode=NumberSelectorMode.BOX)
)
USER_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="username"))
PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password"))


async def _validate_local(hass: HomeAssistant, host: str) -> tuple[str | None, dict[str, str]]:
    try:
        state = await RecuairLocal(async_get_clientsession(hass), host).fetch()
    except RecuairConnectionError:
        return None, {"base": "cannot_connect"}
    except RecuairError:
        return None, {"base": "not_recuair"}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Neočakávaná chyba pri pripájaní k jednotke Recuair")
        return None, {"base": "unknown"}
    return state.name or "Recuair", {}


async def _validate_cloud(
    hass: HomeAssistant, username: str, password: str, device_name: str | None
) -> tuple[int | None, dict[str, str]]:
    cloud = RecuairCloud(async_get_clientsession(hass), username, password)
    try:
        await cloud.login()
        devices = await cloud.devices()
    except RecuairCloudAuthError:
        return None, {"base": "cloud_invalid_auth"}
    except RecuairCloudError:
        return None, {"base": "cloud_cannot_connect"}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Neočakávaná chyba pri prihlásení do cloudu Recuair")
        return None, {"base": "unknown"}
    if not devices:
        return None, {"base": "cloud_no_devices"}
    match = next((d for d in devices if device_name and d.get("name") == device_name), devices[0])
    return int(match["id"]), {}


class RecuairConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pridanie jednotky Recuair."""

    VERSION = 2

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._title = "Recuair"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Adresa jednotky v lokálnej sieti."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            name, errors = await _validate_local(self.hass, host)
            if not errors:
                await self.async_set_unique_id(name)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                self._title = name
                self._data = {CONF_HOST: host, CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
                return await self.async_step_cloud()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): SCAN_SELECTOR,
                }
            ),
            errors=errors,
        )

    async def async_step_cloud(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Voliteľný účet recuair.enobis.eu (otáčky ventilátorov, zrekuperovaná energia)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = (user_input.get(CONF_CLOUD_USERNAME) or "").strip()
            password = user_input.get(CONF_CLOUD_PASSWORD) or ""
            if not username and not password:
                return self.async_create_entry(title=self._title, data=self._data)
            device_id, errors = await _validate_cloud(self.hass, username, password, self._title)
            if not errors:
                return self.async_create_entry(
                    title=self._title,
                    data={
                        **self._data,
                        CONF_CLOUD_USERNAME: username,
                        CONF_CLOUD_PASSWORD: password,
                        CONF_CLOUD_DEVICE_ID: device_id,
                    },
                )
        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_CLOUD_USERNAME): USER_SELECTOR,
                    vol.Optional(CONF_CLOUD_PASSWORD): PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RecuairOptionsFlow()


class RecuairOptionsFlow(OptionsFlow):
    """Zmena adresy, intervalu a účtu v cloude."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            name, errors = await _validate_local(self.hass, host)
            options: dict[str, Any] = {CONF_HOST: host, CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            username = (user_input.get(CONF_CLOUD_USERNAME) or "").strip()
            password = user_input.get(CONF_CLOUD_PASSWORD) or current.get(CONF_CLOUD_PASSWORD) or ""
            if not errors and username:
                device_id, errors = await _validate_cloud(self.hass, username, password, name)
                options.update({CONF_CLOUD_USERNAME: username, CONF_CLOUD_PASSWORD: password, CONF_CLOUD_DEVICE_ID: device_id})
            elif not errors:
                options.update({CONF_CLOUD_USERNAME: "", CONF_CLOUD_PASSWORD: "", CONF_CLOUD_DEVICE_ID: None})
            if not errors:
                return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current.get(CONF_HOST, DEFAULT_HOST)): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ): SCAN_SELECTOR,
                    vol.Optional(
                        CONF_CLOUD_USERNAME, description={"suggested_value": current.get(CONF_CLOUD_USERNAME)}
                    ): USER_SELECTOR,
                    vol.Optional(CONF_CLOUD_PASSWORD): PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
        )
