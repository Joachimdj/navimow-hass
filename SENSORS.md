# Navimow SDK Sensors & States - Implementation Status

## Summary

The integration has been updated to expose **8 sensor entities** from the Navimow SDK's DeviceStatus model. Below is a comprehensive breakdown of what's available in the SDK and what's currently implemented.

## Implemented Sensors (8 Total)

### 1. **Battery** ✅
- **Device Class**: BATTERY  
- **Unit**: % (percentage)
- **State Class**: MEASUREMENT
- **Source**: DeviceStatus.battery
- **Enabled by Default**: Yes
- **Description**: Current battery level percentage (0-100)

### 2. **Signal Strength** ✅
- **Device Class**: SIGNAL_STRENGTH
- **Unit**: dBm (decibels relative to one milliwatt)
- **State Class**: MEASUREMENT  
- **Source**: DeviceStatus.signal_strength
- **Enabled by Default**: Yes
- **Description**: Wireless signal strength indicator

### 3. **Mowing Time** ✅
- **Device Class**: DURATION
- **Unit**: seconds (s)
- **State Class**: TOTAL_INCREASING
- **Source**: DeviceStatus.mowing_time
- **Enabled by Default**: Yes
- **Description**: Duration of current mowing session in seconds

### 4. **Total Mowing Time** ✅
- **Device Class**: DURATION
- **Unit**: seconds (s)
- **State Class**: TOTAL_INCREASING
- **Source**: DeviceStatus.total_mowing_time
- **Enabled by Default**: Yes
- **Description**: Total accumulated mowing time in seconds (lifetime)

### 5. **Error Code** ✅
- **Device Class**: ENUM
- **Unit**: None
- **Source**: DeviceStatus.error_code (MowerError enum)
- **Enabled by Default**: Yes
- **Description**: Current error code (NONE, LOW_BATTERY, OBSTACLE, WHEELS_STUCK, etc.)

### 6. **Error Message** ✅
- **Device Class**: TEXT
- **Unit**: None
- **Source**: DeviceStatus.error_message
- **Enabled by Default**: No (disabled by default for cleaner UI)
- **Description**: Human-readable error message if an error occurred

### 7. **Latitude** ✅
- **Device Class**: LATITUDE
- **Unit**: °
- **State Class**: MEASUREMENT
- **Source**: DeviceStatus.position["lat"]
- **Enabled by Default**: No (disabled by default for privacy)
- **Description**: GPS latitude coordinate of device location

### 8. **Longitude** ✅
- **Device Class**: LONGITUDE
- **Unit**: °
- **State Class**: MEASUREMENT
- **Source**: DeviceStatus.position["lng"]
- **Enabled by Default**: No (disabled by default for privacy)
- **Description**: GPS longitude coordinate of device location

## Lawn Mower Entity

The `lawn_mower` entity exposes device activity state with mappings:
- `idle` → LawnMowerActivity.IDLE
- `mowing` → LawnMowerActivity.MOWING
- `paused` → LawnMowerActivity.PAUSED
- `docked` → LawnMowerActivity.DOCKED
- `charging` → LawnMowerActivity.DOCKED (charging treated as docked)
- `returning` → LawnMowerActivity.RETURNING
- `error` → LawnMowerActivity.ERROR

**Controls Available**:
- Start mowing
- Pause mowing
- Dock/Return to base
- Resume mowing

## SDK Models Available (Not Yet Exposed as Sensors)

### DeviceAttributesMessage
- **device_id**: Device identifier
- **attributes**: Generic dictionary of device attributes
- **Status**: Not yet exposed (could be used for additional device-specific attributes)

### DeviceEventMessage  
- **device_id**: Device identifier
- **timestamp**: Event timestamp
- **type**: Event type (e.g., "system", "user", "device")
- **event**: Event name/identifier
- **level**: Event severity/level
- **message**: Event description text
- **params**: Event parameters dictionary
- **Status**: Not yet exposed (could be added as event listeners/automations)

### DeviceStateMessage (MQTT)
This is a real-time alternative to DeviceStatus and includes:
- **device_id**: Device identifier
- **state**: Normalized mower state
- **battery**: Battery percentage
- **signal_strength**: Signal strength
- **position**: GPS coordinates
- **error**: Error information dict
- **metrics**: Additional metrics dict with raw_state and others
- **timestamp**: Message timestamp
- **Status**: Partially exposed through DeviceStatus (coordinator syncs with MQTT)

## Available Error Codes (MowerError Enum)

Possible values for the error_code sensor:
- `none` - No error
- `low_battery` - Battery too low to operate
- `obstacle` - Obstacle detected
- `wheels_stuck` - Wheels are stuck
- `boundary_error` - Boundary sensor error
- `rain_sensor` - Rain detected
- `too_steep` - Terrain too steep
- `no_signal` - No wireless signal
- `unknown` - Unknown error state

## Available Mower States (MowerStatus Enum)

Possible values for lawn_mower entity state:
- `idle` - Device idle/standby
- `mowing` - Actively mowing
- `paused` - Mowing paused
- `docked` - At charging dock
- `charging` - Charging battery
- `returning` - Returning to dock
- `error` - Error state
- `unknown` - State unknown

## Future Enhancement Opportunities

### Events & Automation
Could expose device events as triggers:
- Battery low warning
- Obstacle detected
- Maintenance needed
- Mowing started/stopped

### Additional Attributes
Could create binary sensors for:
- Is charging
- Is mowing
- Is docked
- Has error
- Battery critically low

### Statistics
Could track:
- Mowing duration per day/week/month
- Area covered (if available in attributes)
- Error frequency
- Signal strength trends

## File Changes

### Updated Files
1. **sensor.py**
   - Added 7 new sensor descriptions (signal_strength, mowing_time, total_mowing_time, error_code, error_message, latitude, longitude)
   - Updated value extraction functions for each sensor
   - Added import for UnitOfTime constant

2. **strings.json**
   - Added translations for all 8 sensor names in entity.sensor.navimow section

## Code Example: Accessing Sensor Values

```python
# From Home Assistant Automation/Template
# Battery
{{ state_attr('sensor.navimow_battery', 'native_value') }}

# Signal Strength  
{{ state_attr('sensor.navimow_signal_strength', 'native_value') }}

# Mowing Time (current session in seconds)
{{ state_attr('sensor.navimow_mowing_time', 'native_value') }}

# Total Mowing Time (lifetime in seconds)
{{ state_attr('sensor.navimow_total_mowing_time', 'native_value') }}

# Error Code
{{ state_attr('sensor.navimow_error_code', 'native_value') }}

# Lawn Mower Activity
{{ state_attr('lawn_mower.navimow', 'activity') }}
```

## Testing Recommendations

1. **Verify all 8 sensors** appear in Home Assistant after adding the integration
2. **Check signal strength** updates in real-time from MQTT
3. **Monitor mowing times** during actual mowing sessions
4. **Test error states** if device generates errors
5. **Verify GPS coordinates** display when device is outside charging dock
6. **Confirm state mappings** by observing lawn mower activity transitions

## Related Documentation

- [Architecture & Design](../ARCHITECTURE.md) - System design and data flow
- [Development Guide](../DEVELOPMENT.md) - Developer setup and customization
- [Implementation Notes](../IMPLEMENTATION_NOTES.md) - Development reference

---

**SDK Version**: navimow-sdk >= 0.1.0  
**HA Version**: 2026.1.0+  
**Last Updated**: 2024  
**Sensor Count**: 8 (fully implemented from SDK)
