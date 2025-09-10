"""
Exception classes for Leisai L7 driver.

This module defines all custom exceptions used in the library.
"""


class L7Exception(Exception):
    """Base exception for all L7 driver errors."""
    pass


class CommunicationError(L7Exception):
    """Raised when communication with the servo fails."""
    
    def __init__(self, message="Communication error occurred", error_code=None):
        self.error_code = error_code
        if error_code:
            message = f"{message} (Error code: 0x{error_code:02X})"
        super().__init__(message)


class ConnectionError(CommunicationError):
    """Raised when connection to the servo cannot be established."""
    pass


class TimeoutError(CommunicationError):
    """Raised when communication times out."""
    pass


class ModbusError(CommunicationError):
    """Raised for Modbus protocol errors."""
    
    EXCEPTION_CODES = {
        0x01: "Illegal function",
        0x02: "Illegal data address",
        0x03: "Illegal data value",
        0x04: "Slave device failure",
        0x05: "Acknowledge",
        0x06: "Slave device busy",
        0x08: "Memory parity error",
        0x0A: "Gateway path unavailable",
        0x0B: "Gateway target device failed to respond"
    }
    
    def __init__(self, exception_code):
        self.exception_code = exception_code
        message = self.EXCEPTION_CODES.get(
            exception_code, 
            f"Unknown Modbus exception (0x{exception_code:02X})"
        )
        super().__init__(f"Modbus exception: {message}", exception_code)


class ParameterError(L7Exception):
    """Raised when parameter operations fail."""
    
    def __init__(self, param_name=None, value=None, message=None):
        self.param_name = param_name
        self.value = value
        
        if message is None:
            if param_name and value is not None:
                message = f"Invalid parameter '{param_name}' value: {value}"
            elif param_name:
                message = f"Parameter error for '{param_name}'"
            else:
                message = "Parameter error"
        
        super().__init__(message)


class InvalidParameterError(ParameterError):
    """Raised when a parameter value is invalid."""
    pass


class ReadOnlyParameterError(ParameterError):
    """Raised when trying to write to a read-only parameter."""
    pass


class ParameterOutOfRangeError(ParameterError):
    """Raised when a parameter value is out of valid range."""
    
    def __init__(self, param_name, value, min_val=None, max_val=None):
        self.min_val = min_val
        self.max_val = max_val
        
        if min_val is not None and max_val is not None:
            message = f"Parameter '{param_name}' value {value} out of range [{min_val}, {max_val}]"
        else:
            message = f"Parameter '{param_name}' value {value} out of range"
        
        super().__init__(param_name, value, message)


class ControlError(L7Exception):
    """Raised when control operations fail."""
    pass


class ServoNotReadyError(ControlError):
    """Raised when servo is not ready for operation."""
    
    def __init__(self, status=None, alarm_code=None):
        self.status = status
        self.alarm_code = alarm_code
        
        message = "Servo not ready"
        if alarm_code:
            message += f" (Alarm: 0x{alarm_code:02X})"
        if status:
            message += f" (Status: {status})"
        
        super().__init__(message)


class MotionError(ControlError):
    """Raised when motion commands fail."""
    pass


class HomingError(MotionError):
    """Raised when homing operation fails."""
    pass


class PathError(MotionError):
    """Raised when PR path operations fail."""
    
    def __init__(self, path_id=None, message=None):
        self.path_id = path_id
        
        if message is None:
            if path_id is not None:
                message = f"Path {path_id} error"
            else:
                message = "Path error"
        
        super().__init__(message)


class InvalidPathError(PathError):
    """Raised when path ID is invalid."""
    
    def __init__(self, path_id):
        super().__init__(path_id, f"Invalid path ID: {path_id} (must be 0-15)")


class AlarmError(L7Exception):
    """Raised when servo has an active alarm."""
    
    def __init__(self, alarm_code, description=None):
        from .constants import ALARM_DESCRIPTIONS
        
        self.alarm_code = alarm_code
        self.description = description or ALARM_DESCRIPTIONS.get(
            alarm_code, 
            f"Unknown alarm (0x{alarm_code:02X})"
        )
        
        super().__init__(f"Servo alarm: {self.description}")


class ConfigurationError(L7Exception):
    """Raised when configuration is invalid."""
    pass


class NotConnectedError(L7Exception):
    """Raised when operation requires connection but driver is not connected."""
    
    def __init__(self):
        super().__init__("Driver not connected to servo")