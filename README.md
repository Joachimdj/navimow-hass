# Navimow for Home Assistant

Monitor and control your Navimow robotic mower directly from Home Assistant using the official Navimow SDK.

## Features

✨ **Mower Control**
- Start/pause/resume mowing
- Return to dock
- Real-time status updates

📊 **Device Monitoring**
- Battery level tracking
- Mower state (idle, mowing, paused, docked, charging, returning, error)
- Real-time MQTT updates with HTTP fallback

🏠 **Home Assistant Integration**
- Native `lawn_mower` entity
- Automatic device discovery
- Full automation support

## Installation

### Prerequisites
- Home Assistant 2026.1.0 or newer
- Navimow account (from the official Navimow app)

### Via HACS (Recommended)

1. Open HACS → Integrations
2. Click the menu (⋮) in the top-right
3. Select "Custom repositories"
4. Add repository: `https://github.com/segwaynavimow/navimow-hass`
5. Select category: **Integration**
6. Search for "Navimow" and install
7. Restart Home Assistant
8. Go to Settings → Devices & Services → Integrations
9. Click "Create Integration" and search for "Navimow"

### Manual Installation

1. Copy the `custom_components/navimow` folder to your `custom_components` directory
2. Restart Home Assistant
3. Set up the integration via Settings → Devices & Services

## Setup

After installation:

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **Create Integration** → Search for **Navimow**
3. Click **Confirm** to authorize Home Assistant
4. You'll be redirected to Navimow's login page
5. Log in with your Navimow account credentials
6. Authorize Home Assistant access
7. After successful authentication, restart Home Assistant

## Architecture

This integration combines:
- **NaviMow SDK** - Device communication and control via REST API and MQTT
- **OAuth2 Authentication** - Secure account authentication via Navimow's official OAuth2 endpoints
- **Home Assistant Integration** - Standard HA entities and automations

### Data Flow

```
Home Assistant (OAuth2 Session)
    ↓
Navimow Auth Server (Token Refresh)
    ↓
MowerAPI (Device Discovery, Status, Commands)
    ↓
NavimowSDK (MQTT Real-time Updates)
    ↓
MQTT Broker (device/state/device_id)
    ↓
Coordinator (Data Update & Caching)
    ↓
Entities (lawn_mower, sensor)
```

## Configuration

The integration is configured entirely through the UI. Key settings are automatically managed:
- OAuth2 token refresh
- MQTT credentials management
- Device discovery
- Real-time update coordination

## Services

### `set_blade_height`
Set the mower blade height (currently not supported via REST API).

## Troubleshooting

### "No devices found"
- Ensure your mower is connected to your home network
- Check that your mower appears in the official Navimow app
- Verify your internet connection

### "MQTT connection failed"
- Check that network access to MQTT broker is not blocked
- If using DNS filtering/ad-blocking, try disabling it temporarily
- Ensure your mower is online and connected

### "Authentication failed"
- Re-authenticate your account via the options menu
- Check that your Navimow account credentials are correct
- Ensure your account can log into the official Navimow app

## Support

For issues and feature requests, visit:
https://github.com/segwaynavimow/navimow-hass/issues

## License

This integration uses the NaviMow SDK, which is licensed under the GPL License.

## About

Segway Navimow Official Integration for Home Assistant

- Website: [navimow.com](https://navimow.com)
- Navimow i2 AWD: https://navimow.com/pages/navimow-i2-awd-robot-lawn-mower
- SDK: https://github.com/segwaynavimow/navimow-sdk
