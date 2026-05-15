"""The Navimow integration."""
import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import NavimowOAuth2Implementation
from .const import (
    DOMAIN,
    CLIENT_ID,
    CLIENT_SECRET,
    API_BASE_URL,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
)
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LAWN_MOWER, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Navimow component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Navimow async_setup called, registering OAuth2 implementation")
    # Register OAuth2 implementation so config flow can find it
    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        NavimowOAuth2Implementation(
            hass,
            DOMAIN,
            CLIENT_ID,
            CLIENT_SECRET,
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Navimow from a config entry."""
    # Lazy import to avoid loading mower_sdk during config flow
    from mower_sdk.api import MowerAPI
    from mower_sdk.errors import MowerAPIError
    from mower_sdk.sdk import NavimowSDK

    from .coordinator import NavimowCoordinator

    hass.data.setdefault(DOMAIN, {})

    def _mask_secret(value: str | None) -> str:
        if not value:
            return "<empty>"
        if len(value) <= 4:
            return "*" * len(value)
        return f"{value[:2]}***{value[-2:]}"

    try:
        # Get OAuth2 implementation
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
        if not isinstance(implementation, NavimowOAuth2Implementation):
            raise ConfigEntryAuthFailed("Invalid OAuth2 implementation")

        # Create OAuth2Session
        oauth_session = config_entry_oauth2_flow.OAuth2Session(
            hass, entry, implementation
        )

        # Get valid access token
        token: dict[str, Any] | None = None
        if hasattr(oauth_session, "async_get_valid_token"):
            try:
                token = await oauth_session.async_get_valid_token()
            except AttributeError:
                token = None
        if not token and hasattr(oauth_session, "async_ensure_token_valid"):
            await oauth_session.async_ensure_token_valid()
            token = oauth_session.token
        if not token and hasattr(oauth_session, "async_get_access_token"):
            access_token_value = await oauth_session.async_get_access_token()
            token = {"access_token": access_token_value} if access_token_value else None
        if not token:
            # Fallback for older HA versions
            token = entry.data.get("token")
        if not token:
            raise ConfigEntryAuthFailed("No valid token available")

        access_token = token.get("access_token")
        if not access_token:
            raise ConfigEntryAuthFailed("No access token in token data")

        # Create MowerAPI instance
        api = MowerAPI(
            session=async_get_clientsession(hass),
            token=access_token,
            base_url=entry.data.get("api_base_url", API_BASE_URL),
        )

        # Discover devices
        try:
            devices = await api.async_get_devices()
            _LOGGER.info("Discovered %d Navimow device(s)", len(devices))
        except MowerAPIError as err:
            _LOGGER.error("Failed to discover devices: %s", err)
            raise ConfigEntryNotReady(f"Failed to discover devices: {err}") from err
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Authentication failed during device discovery: %s", err)
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

        if not devices:
            _LOGGER.warning("No Navimow devices found")

        # Get MQTT connection info and create SDK
        try:
            mqtt_info = await api.async_get_mqtt_user_info()
        except MowerAPIError as err:
            _LOGGER.error("Failed to get MQTT info: %s", err)
            raise ConfigEntryNotReady(f"Failed to get MQTT info: {err}") from err

        mqtt_host = mqtt_info.get("mqttHost") or entry.data.get(
            "mqtt_broker", MQTT_BROKER
        )
        mqtt_url = mqtt_info.get("mqttUrl")
        mqtt_username = mqtt_info.get("userName") or entry.data.get(
            "mqtt_username", MQTT_USERNAME
        )
        mqtt_password = mqtt_info.get("pwdInfo") or entry.data.get(
            "mqtt_password", MQTT_PASSWORD
        )
        mqtt_port = 443 if mqtt_url else entry.data.get("mqtt_port", MQTT_PORT)

        # Parse MQTT URL for WebSocket path
        ws_path = mqtt_url
        if mqtt_url:
            parsed = urlparse(mqtt_url)
            if parsed.scheme in ("ws", "wss") and parsed.hostname:
                if not mqtt_host:
                    mqtt_host = parsed.hostname
                if parsed.port:
                    mqtt_port = parsed.port
                ws_path = parsed.path or "/"
                if parsed.query:
                    ws_path = f"{ws_path}?{parsed.query}"

        auth_headers = {"Authorization": f"Bearer {access_token}"} if ws_path else None

        _LOGGER.info(
            "MQTT connection parameters: broker=%s port=%s mqtt_url=%s ws_path=%s username=%s",
            mqtt_host,
            mqtt_port,
            mqtt_url or "<none>",
            ws_path or "<none>",
            _mask_secret(mqtt_username),
        )

        # Create SDK
        def _create_sdk(api: MowerAPI) -> NavimowSDK:
            sdk = NavimowSDK(
                broker=mqtt_host,
                port=mqtt_port,
                username=mqtt_username,
                password=mqtt_password,
                ws_path=ws_path,
                auth_headers=auth_headers,
                loop=hass.loop,
                records=devices,
                keepalive_seconds=2400,
                reconnect_min_delay=1,
                reconnect_max_delay=60,
            )
            _LOGGER.info(
                "Invoking SDK MQTT connect: broker=%s port=%s ws_path=%s",
                mqtt_host,
                mqtt_port,
                ws_path or "<none>",
            )
            sdk.connect()
            return sdk

        sdk = await hass.async_add_executor_job(_create_sdk, api)
        async_setup_services(hass, api)

        # Create coordinators
        coordinators: dict[str, NavimowCoordinator] = {}
        for device in devices:
            coordinator = NavimowCoordinator(
                hass=hass,
                sdk=sdk,
                api=api,
                device=device,
                oauth_session=oauth_session,
            )
            await coordinator.async_setup()
            await coordinator.async_config_entry_first_refresh()
            coordinators[device.id] = coordinator

        # Store data
        hass.data[DOMAIN][entry.entry_id] = {
            "sdk": sdk,
            "api": api,
            "devices": devices,
            "coordinators": coordinators,
            "oauth_session": oauth_session,
        }

        # Forward to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        return True

    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        _LOGGER.exception("Error setting up Navimow integration: %s", err)
        raise ConfigEntryNotReady(f"Error setting up integration: {err}") from err


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            data = hass.data[DOMAIN][entry.entry_id]
            sdk = data.get("sdk")
            if sdk:
                try:
                    sdk.disconnect()
                except Exception as err:
                    _LOGGER.warning("Error disconnecting MQTT: %s", err)

            hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
