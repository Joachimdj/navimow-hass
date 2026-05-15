"""Lawn mower platform for Navimow integration."""
import logging
from typing import Any

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from mower_sdk.api import MowerAPI
from mower_sdk.models import MowerCommand

from .const import DOMAIN, MOWER_STATUS_TO_ACTIVITY
from .coordinator import NavimowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lawn mower entities from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api: MowerAPI = data["api"]
    devices = data["devices"]
    coordinators: dict[str, NavimowCoordinator] = data["coordinators"]

    entities = []
    for device in devices:
        entities.append(
            NavimowLawnMower(
                coordinator=coordinators[device.id],
                api=api,
                device_id=device.id,
                device_name=device.name,
                device_info=device,
            )
        )

    async_add_entities(entities)


class NavimowLawnMower(CoordinatorEntity[NavimowCoordinator], LawnMowerEntity):
    """Representation of a Navimow lawn mower."""

    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE_MOWING
        | LawnMowerEntityFeature.DOCK
        | LawnMowerEntityFeature.RETURN_TO_BASE
    )
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NavimowCoordinator,
        api: MowerAPI,
        device_id: str,
        device_name: str,
        device_info: Any,
    ) -> None:
        """Initialize the lawn mower entity."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._device_name = device_name
        self._device_info = device_info

        self._attr_name = device_name
        self._attr_unique_id = f"{DOMAIN}_{device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Navimow",
            model=device_info.model or "Unknown",
            sw_version=device_info.firmware_version or None,
            serial_number=device_info.serial_number or device_info.id,
        )

    @property
    def activity(self) -> LawnMowerActivity:
        """Return the current activity."""
        if not self.coordinator.data:
            return LawnMowerActivity.ERROR

        status = self.coordinator.data.get("status")
        if not status:
            return LawnMowerActivity.ERROR

        status_value = str(status.status.value) if hasattr(status.status, "value") else str(status.status)
        activity_str = MOWER_STATUS_TO_ACTIVITY.get(status_value, "error")

        try:
            return LawnMowerActivity(activity_str)
        except ValueError:
            return LawnMowerActivity.ERROR

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        try:
            await self._api.async_send_command(self._device_id, MowerCommand.START)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error starting mower %s: %s", self._device_id, err)
            raise

    async def async_pause_mowing(self) -> None:
        """Pause mowing."""
        try:
            await self._api.async_send_command(self._device_id, MowerCommand.PAUSE)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error pausing mower %s: %s", self._device_id, err)
            raise

    async def async_dock(self) -> None:
        """Dock the mower."""
        try:
            await self._api.async_send_command(self._device_id, MowerCommand.DOCK)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error docking mower %s: %s", self._device_id, err)
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self.coordinator.get_device_state() is not None:
            return True
        return super().available
