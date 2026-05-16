"""DataUpdateCoordinator for Navimow Custom integration."""
import json
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from mower_sdk.api import MowerAPI
from mower_sdk.models import Device, DeviceStatus
from mower_sdk.sdk import NavimowSDK

from .const import (
    DOMAIN,
    HTTP_FALLBACK_MIN_INTERVAL,
    MQTT_STALE_SECONDS,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class NavimowCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Navimow Custom data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        sdk: NavimowSDK,
        api: MowerAPI,
        device: Device,
        oauth_session: config_entry_oauth2_flow.OAuth2Session | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.sdk = sdk
        self.api = api
        self.device = device
        self.oauth_session = oauth_session
        self.data: dict[str, Any] = {}
        self._last_status: DeviceStatus | None = None
        self._last_mqtt_update: float | None = None
        self._last_http_fetch: float | None = None
        self._last_data_source: str | None = None

    async def async_setup(self) -> None:
        self.sdk.on_state(self._handle_state)

    def _build_data(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "status": self._last_status,
            "meta": {
                "last_data_source": self._last_data_source,
                "last_mqtt_update_monotonic": self._last_mqtt_update,
                "last_http_fetch_monotonic": self._last_http_fetch,
            },
        }

    def _log_payload(self, source: str) -> None:
        """Log received payload in JSON for troubleshooting."""
        payload = {
            "source": source,
            "device_id": self.device.id,
            "status": self._last_status,
            "meta": {
                "last_data_source": self._last_data_source,
                "last_mqtt_update_monotonic": self._last_mqtt_update,
                "last_http_fetch_monotonic": self._last_http_fetch,
            },
        }
        try:
            _LOGGER.warning(
                "Navimow payload: %s",
                json.dumps(payload, default=lambda obj: vars(obj), ensure_ascii=True),
            )
        except Exception:
            _LOGGER.warning("Navimow payload (fallback): %s", payload)

    async def _async_ensure_valid_token(self) -> str | None:
        if not self.oauth_session:
            return None
        try:
            token: dict[str, Any] | None
            if hasattr(self.oauth_session, "async_ensure_token_valid"):
                await self.oauth_session.async_ensure_token_valid()
                token = self.oauth_session.token
            elif hasattr(self.oauth_session, "async_get_valid_token"):
                token = await self.oauth_session.async_get_valid_token()
            else:
                token = self.oauth_session.token
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.warning(
                "Token refresh failed (possibly transient): %s", err
            )
            cached = getattr(self.oauth_session, "token", None)
            if cached and cached.get("access_token"):
                token = cached
            else:
                raise ConfigEntryAuthFailed(
                    f"Token refresh failed and no cached token available: {err}"
                ) from err

        if not token or not token.get("access_token"):
            raise ConfigEntryAuthFailed("No access token after refresh")

        access_token = token["access_token"]
        self.api.set_token(access_token)
        return access_token

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self._async_ensure_valid_token()
        except ConfigEntryAuthFailed:
            raise

        cached_status = self.sdk.get_cached_state(self.device.id)
        if cached_status is not None:
            self._last_status = cached_status
            self._last_mqtt_update = time.monotonic()
            self._last_data_source = "mqtt"
            self.data = self._build_data()
            return self.data

        now = time.monotonic()
        is_mqtt_stale = (
            self._last_mqtt_update is None
            or now - self._last_mqtt_update > MQTT_STALE_SECONDS
        )
        can_http_fetch = (
            self._last_http_fetch is None
            or now - self._last_http_fetch > HTTP_FALLBACK_MIN_INTERVAL
        )

        if is_mqtt_stale and can_http_fetch:
            try:
                status = await self.api.async_get_device_status(self.device.id)
                self._last_status = status
                self._last_http_fetch = now
                self._last_data_source = "http_fallback"
            except ConfigEntryAuthFailed:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "HTTP fallback failed for device %s: %s", self.device.id, err
                )

        _LOGGER.debug(
            "Coordinator update: device=%s status=%s source=%s",
            self.device.id,
            self._last_status,
            self._last_data_source,
        )
        self.data = self._build_data()
        self._log_payload("coordinator_update")
        return self.data

    def _handle_state(self, state: Any) -> None:
        device_id = getattr(state, "device_id", None)
        if device_id == self.device.id:
            try:
                status = DeviceStatus(
                    device_id=device_id,
                    status=getattr(state, "status", None),
                    battery=getattr(state, "battery", 0),
                )
                self._last_status = status
                self._last_mqtt_update = time.monotonic()
                self._last_data_source = "mqtt"
                self.data = self._build_data()
                self._log_payload("mqtt_callback")
            except Exception as err:
                _LOGGER.warning("Failed to handle state update: %s", err)

    def get_device_state(self) -> Any:
        return self._last_status
