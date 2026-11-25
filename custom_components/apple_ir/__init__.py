"""The Apple IR Receiver integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .hidraw import HidrawReader, device_id, find_apple_ir_devices

PLATFORMS = [Platform.INFRARED]

type AppleIRConfigEntry = ConfigEntry[HidrawReader]


async def async_setup_entry(hass: HomeAssistant, entry: AppleIRConfigEntry) -> bool:
    """Set up Apple IR Receiver from a config entry."""
    devices = await hass.async_add_executor_job(find_apple_ir_devices)
    if not devices:
        _create_issue(hass, entry, "device_unavailable")
        raise ConfigEntryNotReady("No Apple IR receiver found")

    identity = entry.data.get("device_id", entry.unique_id)
    matches = [
        device for device in devices if device.phys and device_id(device) == identity
    ]
    if len(devices) == 1:
        device = devices[0]
    elif len(matches) == 1:
        device = matches[0]
    else:
        _create_issue(hass, entry, "device_selection_required")
        raise ConfigEntryNotReady("Multiple Apple IR receivers require selection")

    reader = HidrawReader(device.path)
    try:
        await hass.async_add_executor_job(reader.open)
    except OSError as err:
        _create_issue(hass, entry, "device_unavailable")
        raise ConfigEntryNotReady(f"Cannot open {device.path}: {err}") from err

    if entry.data.get("path") != device.path or entry.data.get("device_id") != device_id(device):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "path": device.path, "device_id": device_id(device)}
        )
    entry.runtime_data = reader
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    ir.async_delete_issue(hass, DOMAIN, f"receiver_{entry.entry_id}")
    return True


def _create_issue(hass: HomeAssistant, entry: AppleIRConfigEntry, key: str) -> None:
    """Tell the user how to resolve a receiver setup failure."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"receiver_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=key,
    )


async def async_unload_entry(hass: HomeAssistant, entry: AppleIRConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.close()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: AppleIRConfigEntry) -> None:
    """Remove any outstanding repair when the entry is deleted."""
    ir.async_delete_issue(hass, DOMAIN, f"receiver_{entry.entry_id}")
