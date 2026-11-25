"""Config flow for the Apple IR Receiver integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import DOMAIN
from .hidraw import HidrawDevice, device_id, find_apple_ir_devices


def _device_schema(devices: list[HidrawDevice]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("path"): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=d.path, label=f"{d.name} ({d.path})")
                        for d in devices
                    ]
                )
            )
        }
    )


class AppleIRConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apple IR Receiver."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a receiver automatically when there is only one."""
        devices = await self.hass.async_add_executor_job(find_apple_ir_devices)
        by_path = {device.path: device for device in devices}

        if not devices:
            return self.async_abort(reason="no_devices_found")

        device = (
            by_path.get(user_input["path"])
            if user_input is not None
            else devices[0] if len(devices) == 1 else None
        )
        if device is not None:
            await self.async_set_unique_id(device_id(device))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=device.name,
                data={"path": device.path, "device_id": device_id(device)},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_device_schema(devices),
            errors={"base": "device_not_found"} if user_input is not None else None,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the receiver without changing the entry's entity identity."""
        devices = await self.hass.async_add_executor_job(find_apple_ir_devices)
        by_path = {device.path: device for device in devices}

        if not devices:
            return self.async_abort(reason="no_devices_found")

        device = (
            by_path.get(user_input["path"])
            if user_input is not None
            else devices[0] if len(devices) == 1 else None
        )
        if device is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates={"path": device.path, "device_id": device_id(device)},
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _device_schema(devices),
                {"path": self._get_reconfigure_entry().data["path"]},
            ),
            errors={"base": "device_not_found"} if user_input is not None else None,
        )
