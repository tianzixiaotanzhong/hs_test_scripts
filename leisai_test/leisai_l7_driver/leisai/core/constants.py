"""
Constants and enumerations for Leisai L7 servo drivers.

This module contains all constant values, enumerations, and parameter mappings
used throughout the library.
"""

from enum import IntEnum, IntFlag
from typing import Dict, Tuple


class ControlMode(IntEnum):
    """Servo control modes."""
    POSITION = 0x00
    SPEED = 0x01
    TORQUE = 0x02
    POSITION_SPEED = 0x03
    POSITION_TORQUE = 0x04
    SPEED_TORQUE = 0x05
    PR = 0x06  # PR path control mode


class ServoStatus(IntEnum):
    """Servo operational status."""
    IDLE = 0
    RUNNING = 1
    ERROR = 2
    HOMING = 3
    EMERGENCY_STOP = 4
    DISABLED = 5


class AlarmCode(IntEnum):
    """Servo alarm codes."""
    NO_ALARM = 0x00
    OVER_CURRENT = 0x10
    OVER_VOLTAGE = 0x20
    UNDER_VOLTAGE = 0x21
    DRIVER_OVERHEAT = 0x30
    MOTOR_OVERHEAT = 0x31
    ENCODER_ERROR = 0x40
    ENCODER_COMM_ERROR = 0x41
    ENCODER_DATA_ERROR = 0x42
    POSITION_ERROR = 0x50
    OVER_SPEED = 0x60
    OVER_LOAD = 0x70
    COMMUNICATION_ERROR = 0x80
    EMERGENCY_STOP_INPUT = 0x90
    PARAMETER_ERROR = 0xA0
    MOTOR_MISMATCH = 0xB0
    EEPROM_ERROR = 0xC0


class DISignal(IntFlag):
    """Digital input signal definitions."""
    DI1 = 0x0001
    DI2 = 0x0002
    DI3 = 0x0004
    DI4 = 0x0008
    DI5 = 0x0010
    DI6 = 0x0020
    DI7 = 0x0040
    DI8 = 0x0080
    DI9 = 0x0100


class DOSignal(IntFlag):
    """Digital output signal definitions."""
    DO1_SRDY = 0x0001
    DO2_INP = 0x0002
    DO3_ALM = 0x0004
    DO4_ATLMT = 0x0008
    DO5_ATSPD = 0x0010
    DO6_BRKOFF = 0x0020


class HomingMode(IntEnum):
    """PR homing modes."""
    ORIGIN_FORWARD = 0
    ORIGIN_REVERSE = 1
    LIMIT_FORWARD = 2
    LIMIT_REVERSE = 3
    TORQUE_FORWARD = 4
    TORQUE_REVERSE = 5


# Parameter register address mapping
PARAMETER_ADDRESS: Dict[str, int] = {
    # Basic settings (0x0000 - 0x00FF)
    'control_mode': 0x0002,
    'gear_ratio_numerator': 0x0006,
    'gear_ratio_denominator': 0x0007,
    'reverse_mode': 0x0008,
    'position_error_limit': 0x000E,
    'position_error_clear': 0x000F,
    # Auxiliary/utility (per docs: PA0.22, PA0.25)
    'mode_switch_selector': 0x002D,   # PA0.22 PR<->P/S/T 切换选择（仅当控制模式为PR时有效）
    'aux_function': 0x0033,           # PA0.25 辅助功能（0x1111清当前报警等）
    
    # Gain adjustment (0x0100 - 0x01FF)
    'rigidity_level': 0x0100,
    'auto_tune_mode': 0x0101,
    'position_loop_gain': 0x0102,
    'speed_loop_gain': 0x0103,
    'speed_loop_integral': 0x0104,
    'inertia_ratio': 0x0105,
    'torque_filter_time': 0x0108,
    'gain_switch_mode': 0x010F,
    'model_follow_enable': 0x0112,
    
    # Vibration suppression (0x0200 - 0x02FF)
    'notch1_frequency': 0x0201,
    'notch1_width': 0x0202,
    'notch1_depth': 0x0203,
    'notch2_frequency': 0x0204,
    'notch2_width': 0x0205,
    'notch2_depth': 0x0206,
    'adaptive_filter': 0x020A,
    'low_freq_suppress': 0x020C,
    
    # Speed/Torque control (0x0300 - 0x03FF)
    'speed_command_1': 0x0301,
    'speed_command_2': 0x0302,
    'speed_command_3': 0x0303,
    'torque_limit_1': 0x0315,
    'torque_limit_2': 0x0316,
    'acceleration_time': 0x0319,
    'deceleration_time': 0x031A,
    's_curve_time': 0x031B,
    'speed_reach_range': 0x0322,
    
    # I/O monitor (0x0400 - 0x04FF)
    'di_status': 0x0400,
    'di1_function': 0x0401,
    'di2_function': 0x0402,
    'di3_function': 0x0403,
    'di4_function': 0x0404,
    'di5_function': 0x0405,
    'di6_function': 0x0406,
    'di7_function': 0x0407,
    'di8_function': 0x0408,
    'di9_function': 0x0409,
    'do_status': 0x0410,
    'do1_function': 0x0411,
    'do2_function': 0x0412,
    'do3_function': 0x0413,
    'do4_function': 0x0414,
    'do5_function': 0x0415,
    'do6_function': 0x0416,
    'analog1_offset': 0x0428,
    'analog1_gain': 0x0429,
    
    # Extended settings (0x0500 - 0x05FF)
    'motor_max_speed': 0x0520,
    'dynamic_brake_mode': 0x0515,
    'position_range_limit': 0x0530,
    'software_limit_positive': 0x0531,
    'software_limit_negative': 0x0532,
    
    # Special settings (0x0600 - 0x06FF)
    'gain3_ratio': 0x0606,
    'friction_comp_forward': 0x0608,
    'friction_comp_reverse': 0x0609,
    'absolute_encoder_setup': 0x0660,
    'multi_turn_limit': 0x067F,
    
    # PR control (0x0800 - 0x08FF)
    'pr_control': 0x0800,
    'pr_status': 0x0801,
    'pr_error_code': 0x0802,
    'pr_current_path': 0x0803,
    'pr_current_position': 0x0804,  # 32-bit value starting at 0x0804 (big-endian: 高在前)
    'pr_current_position_h': 0x0804,
    'pr_current_position_l': 0x0805,
    'pr_home_mode': 0x080B,
    'pr_home_offset': 0x080C,  # 32-bit value starting at 0x080C (big-endian: 高在前)
    'pr_home_offset_h': 0x080C,
    'pr_home_offset_l': 0x080D,
    'pr_home_speed_high': 0x080F,
    'pr_home_speed_low': 0x0810,
    'pr_jog_speed': 0x6027,
    'pr_jog_acc': 0x6028,
    'pr_jog_dec': 0x6029,
    
    # Status information (0x0B00 - 0x0BFF)
    'command_position_cmd_unit': 0x0B14,  # 32-bit command position in command units (big-endian)
    'command_position_cmd_unit_h': 0x0B14,
    'command_position_cmd_unit_l': 0x0B15,
    'motor_position_cmd_unit': 0x0B16,  # 32-bit motor position in command units (big-endian)
    'motor_position_cmd_unit_h': 0x0B16,
    'motor_position_cmd_unit_l': 0x0B17,
    'encoder_position': 0x0B1C,  # 32-bit motor position in encoder units (big-endian)
    'encoder_position_h': 0x0B1C,
    'encoder_position_l': 0x0B1D,
    'command_position': 0x0B1A,  # 32-bit command position in encoder units (big-endian)
    'command_position_h': 0x0B1A,
    'command_position_l': 0x0B1B,
    'position_error': 0x0B04,
    'servo_status': 0x0B05,  # 驱动器运行状态
    'motor_speed': 0x0B06,   # 电机速度（未滤波）
    'torque_feedback': 0x0B07,  # 电机力矩
    'pulse_frequency': 0x0B08,
    'analog_input_1': 0x0B0C,
    'analog_input_2': 0x0B0D,
    'dc_bus_voltage': 0x0B0A,
    'driver_temperature': 0x0B0B,
    'di_status': 0x0B11,  # 物理IO输入状态
    'do_status': 0x0B12,  # 物理IO输出状态
    'alarm_code': 0x0B1F,
}

# PR path register base addresses
PR_PATH_BASE = 0x6200
PR_PATH_SIZE = 0x10

# Communication settings
DEFAULT_BAUDRATE = 38400
DEFAULT_TIMEOUT = 1.0
MAX_RETRIES = 3
RETRY_DELAY = 0.1

# Physical limits
MAX_SPEED_RPM = 6500
MAX_ACCELERATION = 10000  # ms/krpm
MAX_POSITION = 2147483647  # 2^31 - 1
MIN_POSITION = -2147483648  # -2^31

# Alarm descriptions
ALARM_DESCRIPTIONS: Dict[int, str] = {
    0x00: "No alarm",
    0x10: "Over current",
    0x20: "DC bus over voltage",
    0x21: "DC bus under voltage",
    0x30: "Driver overheat",
    0x31: "Motor overheat",
    0x40: "Encoder error",
    0x41: "Encoder communication error",
    0x42: "Encoder data error",
    0x50: "Position deviation too large",
    0x60: "Over speed",
    0x70: "Overload",
    0x80: "Communication error",
    0x90: "Emergency stop input",
    0xA0: "Parameter error",
    0xB0: "Motor model mismatch",
    0xC0: "EEPROM error",
    # 系统状态代码（非错误）
    0xFFE0: "System status (normal operation)",
    0xFFF4: "System status (normal operation)", 
    0xFFFC: "System status (normal operation)",
    0xFFEC: "System status (normal operation)",
    0xD06C: "Initialization status (normal during startup)",
}

# 系统状态代码（这些不是真正的错误，可以忽略）
SYSTEM_STATUS_CODES = {
    0xFFE0, 0xFFF4, 0xFFFC, 0xFFEC, 0xD06C
}

# DI function codes
DI_FUNCTIONS: Dict[str, int] = {
    'none': 0x00,
    'servo_on': 0x01,
    'alarm_reset': 0x03,
    'positive_limit': 0x05,
    'negative_limit': 0x06,
    'gain_switch': 0x09,
    'emergency_stop': 0x0E,
    'origin': 0x10,
    'pr_trigger': 0x20,
}

# DO function codes
DO_FUNCTIONS: Dict[str, int] = {
    'none': 0x00,
    'servo_ready': 0x01,
    'in_position': 0x03,
    'alarm': 0x07,
    'at_torque_limit': 0x08,
    'at_speed': 0x09,
    'brake_release': 0x0C,
    'warning': 0x0D,
    'pr_complete': 0x22,
}

# Unit conversion factors
PULSE_PER_REV = 131072  # 17-bit encoder
PULSE_PER_REV_23BIT = 8388608  # 23-bit encoder