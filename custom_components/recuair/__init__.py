"""Integrácia Recuair – rekuperačné jednotky (lokálne + voliteľne cloud)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .cloud import RecuairCloud
from .const import (
    CONF_CLOUD_DEVICE_ID,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import RecuairCloudCoordinator, RecuairCoordinator, RecuairRuntime
from .local import RecuairLocal

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.FAN, Platform.SELECT, Platform.LIGHT]

type RecuairConfigEntry = ConfigEntry[RecuairRuntime]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Prechod z pôvodnej integrácie (verzia 1) bez straty entít a histórie."""
    if entry.version == 1:
        uid = entry.unique_id
        old_prefix = f"{{('{DOMAIN}', '{uid}')}}_"

        @callback
        def _migrate(entity: er.RegistryEntry) -> dict[str, str] | None:
            if entity.unique_id.startswith(old_prefix):
                return {"new_unique_id": f"{uid}_{entity.unique_id[len(old_prefix):]}"}
            return None

        await er.async_migrate_entries(hass, entry.entry_id, _migrate)
        data = {
            CONF_HOST: entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
            CONF_SCAN_INTERVAL: entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        }
        hass.config_entries.async_update_entry(entry, data=data, options={}, version=2)
        _LOGGER.info("Recuair: konfigurácia prevedená na verziu 2 (host %s)", data[CONF_HOST])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RecuairConfigEntry) -> bool:
    """Nastaví jednotku z konfiguračného záznamu."""
    config = {**entry.data, **entry.options}
    session = async_get_clientsession(hass)
    api = RecuairLocal(session, config[CONF_HOST])
    local = RecuairCoordinator(hass, entry, api, config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    await local.async_config_entry_first_refresh()
    runtime = RecuairRuntime(local=local)

    if config.get(CONF_CLOUD_USERNAME) and config.get(CONF_CLOUD_PASSWORD) and config.get(CONF_CLOUD_DEVICE_ID):
        cloud = RecuairCloud(session, config[CONF_CLOUD_USERNAME], config[CONF_CLOUD_PASSWORD])
        runtime.cloud = RecuairCloudCoordinator(hass, entry, cloud, int(config[CONF_CLOUD_DEVICE_ID]))
        # Výpadok cloudu nesmie zablokovať lokálne ovládanie.
        await runtime.cloud.async_refresh()

    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: RecuairConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: RecuairConfigEntry) -> bool:
    """Odstráni integráciu."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
