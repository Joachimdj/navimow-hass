# Development Guide

## Setting Up a Development Environment

### Prerequisites
- Python 3.11+
- Home Assistant 2026.1.0+
- Docker (optional, for running Home Assistant in a container)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/segwaynavimow/navimow-hass.git
   cd navimow-hass
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running Home Assistant with the Integration

#### Option 1: Docker Compose

Create a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  home-assistant:
    image: homeassistant/home-assistant:latest
    container_name: home-assistant
    privileged: true
    ports:
      - "8123:8123"
    volumes:
      - ./config:/config
      - ./custom_components:/config/custom_components
    environment:
      - TZ=UTC
```

Then run:
```bash
docker-compose up -d
```

#### Option 2: Local Installation

1. Create a Home Assistant configuration directory:
   ```bash
   mkdir -p config/custom_components
   cp -r custom_components/navimow config/custom_components/
   ```

2. Run Home Assistant:
   ```bash
   hass -c config
   ```

3. Access at `http://localhost:8123`

### Code Structure

```
custom_components/navimow/
├── __init__.py           # Main integration setup
├── auth.py              # OAuth2 implementation
├── config_flow.py       # Configuration flow (UI)
├── const.py             # Constants and OAuth config
├── coordinator.py       # Data update coordinator
├── lawn_mower.py        # Lawn mower entity
├── sensor.py            # Sensor entities (battery, etc.)
├── services.py          # Custom services
├── manifest.json        # Integration metadata
└── strings.json         # UI translations
```

### Key Components

#### `NavimowOAuth2Implementation` (auth.py)
- Handles OAuth2 authentication with Navimow servers
- Manages token refresh and expiration
- Implements error handling for auth failures

#### `NavimowOAuth2FlowHandler` (config_flow.py)
- Handles the initial setup flow
- Manages reauthentication when tokens expire
- Uses HA's OAuth2 session management

#### `NavimowCoordinator` (coordinator.py)
- Manages device data updates
- Coordinates between MQTT (real-time) and HTTP (fallback) updates
- Ensures tokens are refreshed before each update

#### `NavimowLawnMower` (lawn_mower.py)
- Lawn mower entity for HA
- Supports start, pause, resume, dock commands
- Tracks mower activity state

#### `NavimowSensor` (sensor.py)
- Battery level sensor
- Additional sensors can be added here

### Testing

1. **Manual Testing:**
   - Set up the integration via the UI
   - Check that devices are discovered
   - Test mower control (start, pause, dock)
   - Verify battery sensor updates
   - Monitor logs for errors

2. **Log Monitoring:**
   ```bash
   # In Home Assistant UI:
   # Settings → Developer Tools → Logs
   # Or command line:
   grep -i navimow config/home-assistant.log
   ```

### Debugging

Enable debug logging in Home Assistant:
```yaml
logger:
  logs:
    custom_components.navimow: debug
    mower_sdk: debug
```

### Integration with NaviMow SDK

The integration uses the official `navimow-sdk` package:
- **MowerAPI**: REST API for device management
- **NavimowSDK**: MQTT client for real-time updates
- **Device**: Device model from SDK

### Common Tasks

#### Adding a New Sensor

1. Add sensor description to `SENSOR_DESCRIPTIONS` in `sensor.py`
2. Update `const.py` if needed
3. Test the sensor in HA UI

#### Adding a New Service

1. Create service handler in `services.py`
2. Register in `async_setup_services()` in `__init__.py`
3. Add service definition to `strings.json`

#### Handling New Device States

1. Update `MOWER_STATUS_TO_ACTIVITY` in `const.py`
2. Update `NavimowLawnMower.activity` property if needed
3. Test with actual device

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m "Add feature X"`
6. Push and create a Pull Request

## Troubleshooting Development

### "Module not found" errors
```bash
# Ensure SDK is installed
pip install navimow-sdk

# Or install from source:
pip install -e ../navimow-sdk
```

### MQTT connection issues
- Check MQTT broker is accessible
- Verify credentials in HA logs
- Check firewall rules (ports 1883 or 443 for WSS)

### OAuth token issues
- Check client credentials in `const.py`
- Monitor token refresh in logs
- Verify Navimow OAuth endpoints are accessible

### Integration not loading
1. Check syntax: `python -m py_compile custom_components/navimow/*.py`
2. Verify `manifest.json` is valid JSON
3. Check HA logs for specific errors
4. Restart HA and clear browser cache

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [NaviMow SDK](https://github.com/segwaynavimow/navimow-sdk)
- [NaviMow Website](https://navimow.com)
