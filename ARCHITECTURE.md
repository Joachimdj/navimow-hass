# Architecture & Design

## Overview

This Home Assistant integration combines the official NaviMow SDK with Home Assistant's OAuth2 framework to provide a seamless, secure integration for controlling Navimow robotic mowers.

## Design Philosophy

1. **SDK-First Approach**: Leverages the official `navimow-sdk` for all device communication, ensuring compatibility and maintainability
2. **OAuth2 Security**: Uses Home Assistant's native OAuth2 implementation with Navimow's official OAuth2 endpoints
3. **Hybrid Data Flow**: Combines real-time MQTT updates with HTTP fallback for reliability
4. **Async/Await**: Fully async design for non-blocking operations
5. **Coordinator Pattern**: Uses HA's `DataUpdateCoordinator` for efficient data management

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Home Assistant                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Integration (__init__.py)                 │   │
│  │  - Entry setup/teardown                              │   │
│  │  - OAuth2 session management                         │   │
│  │  - SDK initialization                                │   │
│  └──────────────────────────────────────────────────────┘   │
│            ↓                      ↓                          │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │  Coordinator        │  │  OAuth2Session      │           │
│  │  - Data updates     │  │  - Token management │           │
│  │  - MQTT/HTTP sync   │  │  - Token refresh    │           │
│  │  - State caching    │  │  - Error handling   │           │
│  └─────────────────────┘  └─────────────────────┘           │
│            ↓                      ↓                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              NaviMow SDK (mower_sdk)                 │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  MowerAPI          │  NavimowSDK/MQTT                │   │
│  │  - async_get_      │  - MQTT connection              │   │
│  │    devices()       │  - Real-time updates            │   │
│  │  - async_get_      │  - Command publishing           │   │
│  │    device_status() │  - Credential refresh           │   │
│  │  - async_send_     │                                 │   │
│  │    command()       │                                 │   │
│  │  - async_get_mqtt_ │                                 │   │
│  │    user_info()     │                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│            ↓                      ↓                          │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │   Navimow           │  │   MQTT Broker       │           │
│  │   REST API          │  │   (mqtt.navimow.com)│           │
│  │   Server            │  │   (MQTT/WSS)        │           │
│  └─────────────────────┘  └─────────────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Entities                                  │   │
│  │  - LawnMower (lawn_mower.py)                         │   │
│  │  - Battery Sensor (sensor.py)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Initialization Flow

```
Config Flow (config_flow.py)
    ↓
OAuth2 Login (auth.py)
    ↓
Token Obtained
    ↓
async_setup_entry (__init__.py)
    ├─ Create MowerAPI
    ├─ Discover Devices
    ├─ Get MQTT Info
    ├─ Create NavimowSDK (MQTT)
    └─ Create Coordinators per device
        ↓
Entities Created & Setup
    ↓
Integration Ready
```

### Update Flow

```
Coordinator.async_update_data()
    ├─ Refresh OAuth Token
    ├─ Check MQTT Cached State
    │  └─ If fresh: Return MQTT data
    │
    ├─ Check MQTT Staleness
    │  └─ If stale & time for HTTP:
    │     ├─ Call HTTP API
    │     └─ Update status
    │
    └─ Update Entities
```

### MQTT Callback Flow

```
MQTT Message Received (device/state/device_id)
    ↓
NavimowSDK._on_mqtt_message()
    ↓
SDK State Callback (coordinator._handle_state)
    ↓
Update Coordinator Data
    ↓
Update Entities
    ↓
Trigger State Change Event
```

## Key Design Decisions

### 1. OAuth2 Integration

**Why**: Security and user convenience
- Users log in via their Navimow account
- Tokens are managed by Home Assistant
- Automatic token refresh handled transparently
- No password storage in HA

**Implementation**:
- `NavimowOAuth2Implementation` extends `LocalOAuth2Implementation`
- Token refresh distinguishes auth failures from transient errors
- Fallback to cached token on transient failures

### 2. Hybrid MQTT/HTTP Architecture

**Why**: Reliability and responsiveness
- MQTT provides real-time updates (low latency)
- HTTP provides fallback when MQTT is stale or down
- Configurable timeouts to balance bandwidth and latency

**Implementation**:
```python
# Check MQTT first (real-time, efficient)
cached = sdk.get_cached_state(device_id)

# Fall back to HTTP if stale
if mqtt_stale and time_for_http:
    status = await api.async_get_device_status(device_id)
```

### 3. Coordinator Pattern

**Why**: Efficient data management
- Centralized update logic per device
- Prevents duplicate API calls
- Automatic retry logic
- Clean entity access pattern

**Implementation**:
- `NavimowCoordinator` extends HA's `DataUpdateCoordinator`
- Entities are `CoordinatorEntity` subclasses
- Data updates coordinated via `coordinator.data`

### 4. Async/Await Throughout

**Why**: Non-blocking, responsive HA
- All I/O operations are async
- Integration doesn't block HA event loop
- Proper error handling and timeouts

### 5. Lazy SDK Import

**Why**: Config flow performance
- SDK not imported until setup, not during config flow
- Faster config UI response
- Avoids loading dependencies if not needed

```python
# In __init__.py async_setup_entry:
from mower_sdk.api import MowerAPI  # Only imported here, not in config_flow.py
```

## Token Refresh Strategy

The integration handles three scenarios:

1. **Normal Refresh**: Token expires naturally
   - HA automatically refreshes via `oauth_session`
   - Integration detects and updates API token
   - Coordinator ensures token freshness before each update

2. **MQTT Disconnection**: Triggers credential refresh
   - On disconnect callback: refresh token + MQTT credentials
   - Prevents "invalid auth" errors on reconnect
   - Syncs OAuth token with MQTT credentials

3. **Auth Failure**: Deterministic vs Transient
   - **Deterministic** (401, 403, no refresh_token): Trigger re-auth
   - **Transient** (network, timeout): Use cached token, retry later

## Error Handling

### ConfigEntryAuthFailed
Raised when:
- No access token available
- Token refresh fails (deterministic)
- OAuth session invalid

**Result**: HA displays "re-authentication required" in UI

### ConfigEntryNotReady
Raised when:
- Device discovery fails
- MQTT info retrieval fails
- Network connectivity issues

**Result**: HA retries setup after configured delay

### MowerAPIError
Raised by SDK for:
- Device not found
- Command failed
- API errors

**Result**: Logged, coordinator marks data unavailable

## Entity Design

### LawnMowerEntity
**Attributes**:
- `activity`: Maps device status to HA activity state
- `supported_features`: START, PAUSE, DOCK, RETURN_TO_BASE

**Actions**:
- `async_start_mowing()`: Command via API
- `async_pause_mowing()`: Command via API
- `async_dock()`: Command via API

**Availability**: Tracks coordinator availability

### SensorEntity
**Battery Sensor**:
- Unit: %
- Device class: BATTERY
- State class: MEASUREMENT
- Value source: Coordinator data

## Extensibility

### Adding New Entities

1. **Sensor**:
   ```python
   NavimowSensorEntityDescription(
       key="new_sensor",
       device_class=SensorDeviceClass.SPEED,
       value_fn=lambda coordinator: coordinator.data["status"].speed,
   )
   ```

2. **Service**:
   ```python
   async def _handle_service(call: ServiceCall):
       # Handler
   hass.services.async_register(DOMAIN, "service_name", _handle_service)
   ```

### Device Discovery

Automatically discovers all devices linked to the account:
- Retrieves via `api.async_get_devices()`
- Creates coordinator per device
- Entities automatically populated

## Performance Considerations

1. **Update Interval**: 30 seconds (configurable)
2. **MQTT Timeout**: 5 minutes (stale threshold)
3. **HTTP Fallback**: 1 hour minimum between HTTP calls
4. **Token Refresh**: Before every coordinator update
5. **Batch Operations**: Device updates parallelized

## Security

1. **OAuth2**: Standard implementation, no password storage
2. **Token Refresh**: Automatic, transparent to users
3. **MQTT Auth**: Bearer token in WebSocket headers
4. **Error Messages**: Masked secrets in logs
5. **Secrets Masking**: Passwords/tokens shown as `***` in debug logs

## Future Enhancements

1. **Additional Sensors**: GPS location, blade height, error codes
2. **Device Customization**: Per-device settings in options flow
3. **Statistics**: Mowing duration, area covered, error tracking
4. **Scene Support**: Predefined mowing patterns
5. **Climate Integration**: Weather-aware mowing
