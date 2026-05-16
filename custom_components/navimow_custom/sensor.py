"""Sensor platform for Navimow Custom integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NavimowCoordinator


@dataclass(frozen=True, kw_only=True)
class NavimowSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[NavimowCoordinator], Any]


SENSOR_DESCRIPTIONS: tuple[NavimowSensorEntityDescription, ...] = (
    NavimowSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: (
            status.battery if (status := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="signal_strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
        value_fn=lambda coordinator: (
            status.signal_strength if (status := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="mowing_time",
        translation_key="mowing_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=True,
        value_fn=lambda coordinator: (
            status.mowing_time if (status := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="total_mowing_time",
        translation_key="total_mowing_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=True,
        value_fn=lambda coordinator: (
            status.total_mowing_time if (status := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        device_class=SensorDeviceClass.ENUM,
        entity_registry_enabled_default=True,
        value_fn=lambda coordinator: (
            status.error_code.value if (status := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="error_message",
        translation_key="error_message",
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: (
            status.error_message if (status := coordinator.get_device_state()) else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="latitude",
        translation_key="latitude",
        device_class=SensorDeviceClass.LATITUDE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: (
            position.get("lat")
            if (status := coordinator.get_device_state()) and (position := status.position)
            else None
        ),
    ),
    NavimowSensorEntityDescription(
        key="longitude",
        translation_key="longitude",
        device_class=SensorDeviceClass.LONGITUDE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: (
            position.get("lng")
            if (status := coordinator.get_device_state()) and (position := status.position)
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    devices = data["devices"]
    coordinators: dict[str, NavimowCoordinator] = data["coordinators"]

    entities: list[NavimowSensor] = []
    for device in devices:
        coordinator = coordinators[device.id]
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                NavimowSensor(
                    coordinator=coordinator,
                    entity_description=description,
                )
            )
    async_add_entities(entities)


class NavimowSensor(CoordinatorEntity[NavimowCoordinator], SensorEntity):
    entity_description: NavimowSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NavimowCoordinator,
        entity_description: NavimowSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description

        device = coordinator.device
        self._attr_unique_id = f"{DOMAIN}_{device.id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="Navimow",
            model=device.model or "Unknown",
            sw_version=device.firmware_version or None,
            serial_number=device.serial_number or device.id,
        )

    @property
    def available(self) -> bool:
        if self.coordinator.get_device_state() is not None:
            return True
        return super().available

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)
