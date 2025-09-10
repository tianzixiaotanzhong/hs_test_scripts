# Leisai L7 Servo Driver

A professional Python driver library for Leisai L7/L7RS/L7EC series AC servo controllers, implementing complete Modbus RTU communication protocol with comprehensive motion control capabilities.

## Features

- **Complete Modbus RTU Implementation** - Full protocol support with CRC16 validation and automatic retry mechanism
- **Multiple Control Modes** - Position, speed, and torque control with seamless switching
- **PR Path Control** - Advanced path planning with up to 16 configurable motion paths
- **Real-time Monitoring** - Continuous status monitoring with callback support
- **Parameter Management** - Read/write parameters with import/export capabilities
- **Professional Architecture** - Modular design following Python standard library patterns
- **Type Hints** - Full type annotation support for better IDE integration
- **Thread Safety** - Safe for multi-threaded applications

## Installation

### From PyPI (recommended)
```bash
pip install leisai-l7-driver
```

### From Source
```bash
git clone https://github.com/leisai/python-l7-driver.git
cd python-l7-driver
pip install -e .
```

### Development Installation
```bash
pip install -e .[dev]
```

## Quick Start

```python
from leisai import L7Driver, ControlMode

# Connect to servo
driver = L7Driver('COM3', slave_id=1)
driver.connect()

# Basic operations
driver.servo_on()
position = driver.get_position()
driver.set_control_mode(ControlMode.SPEED)
driver.jog(speed=500, direction=True)

# Cleanup
driver.servo_off()
driver.disconnect()
```

### Using Context Manager

```python
from leisai import L7Driver

with L7Driver('COM3') as driver:
    driver.servo_on()
    print(f"Position: {driver.get_position()}")
    # Auto disconnect on exit
```

## Documentation

### Control Modes

#### Position Control
```python
driver.set_control_mode(ControlMode.POSITION)
driver.write_parameter('gear_ratio_numerator', 10000)
driver.write_parameter('gear_ratio_denominator', 131072)
driver.write_parameter('position_loop_gain', 250)
```

#### Speed Control
```python
driver.set_control_mode(ControlMode.SPEED)
driver.write_parameter('speed_command_1', 1000)  # 1000 rpm
driver.write_parameter('acceleration_time', 500)  # 500ms
```

#### Torque Control
```python
driver.set_control_mode(ControlMode.TORQUE)
driver.write_parameter('torque_limit_1', 80)  # 80% limit
```

### Motion Control

#### JOG Motion
```python
# Start JOG
driver.jog(speed=200, direction=True)  # Forward at 200 rpm

# Stop JOG
driver.stop_jog()
```

#### Homing
```python
# Start homing sequence
driver.home(mode=0, high_speed=500, low_speed=50)

# Wait for completion
while not driver.is_homing_complete():
    time.sleep(0.1)
```

#### PR Path Control
```python
from leisai.core.motion import PRPath

# Configure path
path = PRPath(
    path_id=0,
    position=10000,
    speed=1000,
    acceleration=100,
    deceleration=100,
    delay=500,
    s_curve=10
)

# Set and execute
driver._motion.set_pr_path(path)
driver._motion.execute_pr_path(0)
```

### Parameter Management

```python
# Read parameters
rigidity = driver.read_parameter('rigidity_level')
inertia = driver.read_parameter('inertia_ratio')

# Write parameters
driver.set_rigidity(20)
driver.set_inertia_ratio(200)

# Save to EEPROM
driver.save_parameters()

# Export/Import
driver.export_parameters('config.json')
driver.import_parameters('config.json')
```

### Status Monitoring

```python
# Setup callbacks
def on_status_change(status):
    print(f"Position: {status['position']}")

def on_alarm(alarm_code):
    print(f"Alarm: 0x{alarm_code:02X}")

driver.set_status_callback(on_status_change)
driver.set_alarm_callback(on_alarm)

# Check status
if driver.is_ready():
    print("Servo ready")

alarm = driver.get_alarm()
print(driver.get_alarm_description(alarm))
```

## Architecture

The library follows a modular architecture inspired by Python standard library design:

```
leisai/
├── __init__.py           # Public API
├── core/                 # Core functionality
│   ├── driver.py        # Main driver class
│   ├── constants.py     # Constants and enums
│   ├── exceptions.py    # Custom exceptions
│   ├── parameters.py    # Parameter management
│   ├── motion.py        # Motion control
│   └── monitor.py       # Status monitoring
├── protocols/           # Communication protocols
│   ├── modbus.py       # Modbus RTU implementation
│   └── serial.py       # Serial communication
└── utils/              # Utility functions
```

### Key Classes

- **L7Driver** - Main interface for servo control
- **ModbusRTU** - Low-level Modbus protocol handler
- **ParameterManager** - Parameter read/write operations
- **MotionController** - Motion control functionality
- **StatusMonitor** - Real-time status monitoring

### Design Principles

1. **Separation of Concerns** - Each module has a single, well-defined responsibility
2. **Dependency Injection** - Components receive dependencies through constructors
3. **Type Safety** - Comprehensive type hints throughout the codebase
4. **Error Handling** - Hierarchical exception system with specific error types
5. **Thread Safety** - Proper locking for concurrent operations
6. **Resource Management** - Context managers for automatic cleanup

## API Reference

### L7Driver

Main driver class providing high-level servo control interface.

#### Constructor
```python
L7Driver(
    port: str,
    slave_id: int = 1,
    baudrate: int = 38400,
    timeout: float = 1.0
)
```

#### Connection Methods
- `connect() -> bool` - Connect to servo
- `disconnect()` - Disconnect from servo
- `is_connected -> bool` - Check connection status

#### Control Methods
- `servo_on() -> bool` - Enable servo
- `servo_off() -> bool` - Disable servo
- `emergency_stop() -> bool` - Trigger emergency stop
- `reset_alarm() -> bool` - Reset active alarm
- `set_control_mode(mode: ControlMode) -> bool` - Set control mode

#### Motion Methods
- `get_position() -> Optional[int]` - Get current position
- `get_speed() -> Optional[int]` - Get current speed
- `get_torque() -> Optional[int]` - Get current torque
- `jog(speed: int, direction: bool) -> bool` - Start JOG motion
- `home(mode: int, high_speed: int, low_speed: int) -> bool` - Start homing

#### Parameter Methods
- `read_parameter(name: str) -> Optional[Any]` - Read parameter
- `write_parameter(name: str, value: Any) -> bool` - Write parameter
- `save_parameters() -> bool` - Save to EEPROM
- `restore_defaults() -> bool` - Restore factory defaults

## Testing

Run tests using pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=leisai

# Run specific test file
pytest tests/test_modbus.py
```

## Examples

See the `examples/` directory for complete usage examples:

- `basic_usage.py` - Common operations and control modes
- `advanced_control.py` - Advanced features and tuning
- `multi_axis.py` - Controlling multiple servos
- `parameter_config.py` - Parameter management

## Error Handling

The library provides a comprehensive exception hierarchy:

```python
from leisai.core.exceptions import *

try:
    driver.connect()
except ConnectionError:
    print("Failed to connect")
except ModbusError as e:
    print(f"Modbus error: {e.exception_code}")
except AlarmError as e:
    print(f"Servo alarm: {e.description}")
```

## Supported Hardware

- **Servo Drivers**: L7, L7RS, L7EC series
- **Power Range**: 100W - 2000W
- **Communication**: RS232/RS485 Modbus RTU
- **Encoder**: 17-bit/23-bit absolute encoder support

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: [https://leisai-l7-driver.readthedocs.io](https://leisai-l7-driver.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/leisai/python-l7-driver/issues)
- **Discussions**: [GitHub Discussions](https://github.com/leisai/python-l7-driver/discussions)

## Version History

### v1.0.0 (2025-01-04)
- Initial release with full Modbus RTU support
- Position, speed, and torque control modes
- PR path control functionality
- Real-time status monitoring
- Comprehensive parameter management