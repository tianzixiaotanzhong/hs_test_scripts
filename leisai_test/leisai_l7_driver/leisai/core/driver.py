"""
Main driver class for Leisai L7 servo.

This module provides the high-level interface for controlling L7 servo drivers.
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from threading import Thread, Event
from dataclasses import dataclass

from .constants import (
    ControlMode, ServoStatus, AlarmCode,
    PARAMETER_ADDRESS, ALARM_DESCRIPTIONS,
    PR_PATH_BASE, PR_PATH_SIZE, DOSignal
)
from .exceptions import (
    NotConnectedError, ServoNotReadyError,
    ParameterError, ParameterOutOfRangeError,
    InvalidPathError, AlarmError
)
from .parameters import ParameterManager
from .motion import MotionController
from .monitor import StatusMonitor
from ..protocols.serial import SerialConnection
from ..protocols.modbus import ModbusClient

logger = logging.getLogger(__name__)


@dataclass
class ServoInfo:
    """Servo information data class."""
    model: str = ""
    firmware_version: str = ""
    serial_number: str = ""
    rated_power: float = 0.0
    rated_torque: float = 0.0
    rated_speed: int = 3000
    max_speed: int = 6000
    encoder_resolution: int = 131072


class L7Driver:
    """
    Main driver class for Leisai L7 servo.
    
    This class provides the high-level interface for controlling L7 servo drivers,
    including parameter management, motion control, and status monitoring.
    
    Parameters
    ----------
    port : str
        Serial port name (e.g., 'COM3' or '/dev/ttyUSB0')
    slave_id : int, optional
        Modbus slave ID (default: 1)
    baudrate : int, optional
        Serial baudrate (default: 38400)
    timeout : float, optional
        Communication timeout in seconds (default: 1.0)
    
    Examples
    --------
    >>> from leisai import L7Driver
    >>> driver = L7Driver('COM3')
    >>> driver.connect()
    >>> driver.set_control_mode(ControlMode.POSITION)
    >>> position = driver.get_position()
    >>> driver.disconnect()
    
    Using context manager:
    >>> with L7Driver('COM3') as driver:
    ...     driver.servo_on()
    ...     driver.jog(speed=500)
    """
    
    def __init__(
        self,
        port: str,
        slave_id: int = 1,
        baudrate: int = 38400,
        timeout: float = 1.0,
        **kwargs
    ):
        """Initialize L7 driver."""
        # Communication layer
        self._serial = SerialConnection(port, baudrate, timeout, **kwargs)
        self._modbus = ModbusClient(self._serial, slave_id)
        
        # Component managers
        self._params = ParameterManager(self._modbus)
        self._motion = MotionController(self._modbus, self._params)
        self._monitor = StatusMonitor(self._modbus, self._params)
        
        # State
        self._connected = False
        self._servo_info = ServoInfo()
        self._control_mode = ControlMode.POSITION
        self._status = ServoStatus.IDLE
        
        # Callbacks
        self._status_callback: Optional[Callable] = None
        self._alarm_callback: Optional[Callable] = None
        
        logger.info(f"L7Driver initialized for {port} (slave ID: {slave_id})")
    
    # ==================== Connection Management ====================
    
    def connect(self) -> bool:
        """
        Connect to servo driver.
        
        Returns
        -------
        bool
            True if connection successful
            
        Raises
        ------
        ConnectionError
            If connection fails
        """
        if self._connected:
            logger.debug("Already connected")
            return True
        
        try:
            # Open serial connection
            if not self._serial.connect():
                return False
            
            # Test communication
            alarm = self._params.read('alarm_code')
            if alarm is None:
                logger.error("Failed to verify connection")
                self._serial.disconnect()
                return False
            
            self._connected = True
            logger.info(f"Connected to L7 servo (alarm: 0x{alarm:02X})")
            
            # Read servo info
            self._read_servo_info()
            
            # Start monitoring if callbacks are set
            if self._status_callback or self._alarm_callback:
                self._monitor.start(
                    status_callback=self._status_callback,
                    alarm_callback=self._alarm_callback
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._serial.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from servo driver."""
        if not self._connected:
            return
        
        # Stop monitoring
        self._monitor.stop()
        
        # Close connection
        self._serial.disconnect()
        self._connected = False
        logger.info("Disconnected from L7 servo")
    
    @property
    def is_connected(self) -> bool:
        """Check if driver is connected."""
        return self._connected and self._serial.is_connected
    
    def _check_connection(self):
        """Raise exception if not connected."""
        if not self.is_connected:
            raise NotConnectedError()
    
    # ==================== Servo Control ====================
    
    def servo_on(self) -> bool:
        """
        Enable servo.
        
        Note: L7 servo enable requires external IO control (SRV-ON signal).
        
        Returns
        -------
        bool
            Always raises ServoNotReadyError
            
        Raises
        ------
        NotConnectedError
            If not connected
        ServoNotReadyError
            Always raised - requires external IO control
        """
        self._check_connection()
        
        # Check for alarms
        alarm = self.get_alarm()
        if alarm != AlarmCode.NO_ALARM:
            raise ServoNotReadyError(alarm_code=alarm)
        
        raise ServoNotReadyError(
            message="L7 servo enable requires external IO control (SRV-ON signal)."
        )
    
    def servo_off(self) -> bool:
        """
        Disable servo.
        
        Note: L7 servo disable requires external IO control (SRV-ON signal).
        
        Returns
        -------
        bool
            Always raises ServoNotReadyError
            
        Raises
        ------
        NotConnectedError
            If not connected
        ServoNotReadyError
            Always raised - requires external IO control
        """
        self._check_connection()
        
        raise ServoNotReadyError(
            message="L7 servo disable requires external IO control (SRV-ON signal)."
        )

    def is_servo_on(self) -> bool:
        """
        Check whether servo is enabled.

        Returns
        -------
        bool
            True if servo is enabled
        """
        self._check_connection()

        try:
            do_status = self._params.read('do_status')
            if do_status is None:
                return False
            return (int(do_status) & int(DOSignal.DO1_SRDY)) != 0
        except Exception:
            return False
    
    def emergency_stop(self) -> bool:
        """
        Trigger emergency stop.
        
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        
        logger.warning("Emergency stop triggered")
        self._status = ServoStatus.EMERGENCY_STOP
        
        # TODO: Implement proper emergency stop via DI or register
        return self.servo_off()
    
    def reset_alarm(self) -> bool:
        """
        Reset servo alarm via auxiliary function register.
        
        Docs: Write 0x1111 to PA0.25 (aux_function) to clear current alarm.
        Optionally write 0x1122 to clear history.
        """
        self._check_connection()
        
        logger.info("Resetting alarm")
        try:
            success = self._params.write('aux_function', 0x1111)
            if not success:
                return False
            time.sleep(0.05)
            return True
        except Exception as e:
            logger.error(f"Failed to reset alarm: {e}")
            return False
    
    def set_control_mode(self, mode: ControlMode) -> bool:
        """
        Set control mode.
        
        Parameters
        ----------
        mode : ControlMode
            Control mode to set
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        ParameterError
            If mode is invalid
        """
        self._check_connection()
        
        if not isinstance(mode, ControlMode):
            raise ParameterError("mode", mode, "Invalid control mode")
        
        logger.info(f"Setting control mode to {mode.name}")
        success = self._params.write('control_mode', mode.value)
        
        if success:
            self._control_mode = mode
        
        return success
    
    @property
    def control_mode(self) -> ControlMode:
        """Get current control mode."""
        return self._control_mode
    
    # ==================== Motion Control ====================
    
    def get_position(self) -> Optional[int]:
        """
        Get current position in pulses.
        
        Returns
        -------
        Optional[int]
            Position in pulses, None if failed
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.get_position()
    
    def get_command_position(self) -> Optional[int]:
        """
        Get commanded position in pulses.
        
        Returns
        -------
        Optional[int]
            Command position in pulses, None if failed
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.get_command_position()
    
    def get_speed(self) -> Optional[int]:
        """
        Get current speed in rpm.
        
        Returns
        -------
        Optional[int]
            Speed in rpm, None if failed
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.get_speed()
    
    def get_torque(self) -> Optional[int]:
        """
        Get current torque percentage.
        
        Returns
        -------
        Optional[int]
            Torque percentage, None if failed
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.get_torque()
    
    def jog(self, speed: int, direction: bool = True) -> bool:
        """
        Start JOG motion.
        
        Parameters
        ----------
        speed : int
            Speed in rpm
        direction : bool
            True for forward, False for reverse
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.jog(speed, direction)
    
    def stop_jog(self) -> bool:
        """
        Stop JOG motion.
        
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.stop_jog()
    
    def home(self, mode: int = 0, high_speed: int = 500, low_speed: int = 50) -> bool:
        """
        Start homing sequence.
        
        Parameters
        ----------
        mode : int
            Homing mode
        high_speed : int
            High speed in rpm
        low_speed : int
            Low speed in rpm
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        self._status = ServoStatus.HOMING
        return self._motion.home(mode, high_speed, low_speed)
    
    def is_homing_complete(self) -> bool:
        """
        Check if homing is complete.
        
        Returns
        -------
        bool
            True if homing complete
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._motion.is_homing_complete()
    
    # ==================== Parameter Management ====================
    
    def read_parameter(self, name: str) -> Optional[Any]:
        """
        Read parameter by name.
        
        Parameters
        ----------
        name : str
            Parameter name
            
        Returns
        -------
        Optional[Any]
            Parameter value, None if failed
            
        Raises
        ------
        NotConnectedError
            If not connected
        ParameterError
            If parameter name invalid
        """
        self._check_connection()
        return self._params.read(name)
    
    def write_parameter(self, name: str, value: Any) -> bool:
        """
        Write parameter by name.
        
        Parameters
        ----------
        name : str
            Parameter name
        value : Any
            Parameter value
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        ParameterError
            If parameter name invalid or value out of range
        """
        self._check_connection()
        return self._params.write(name, value)
    
    def save_parameters(self) -> bool:
        """
        Save parameters to EEPROM.
        
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.save_to_eeprom()
    
    def restore_defaults(self) -> bool:
        """
        Restore factory default parameters.
        
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.restore_defaults()
    
    def export_parameters(self, filename: str) -> bool:
        """
        Export parameters to file.
        
        Parameters
        ----------
        filename : str
            Output filename
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.export_to_file(filename)
    
    def import_parameters(self, filename: str) -> bool:
        """
        Import parameters from file.
        
        Parameters
        ----------
        filename : str
            Input filename
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.import_from_file(filename)
    
    # ==================== Gain Adjustment ====================
    
    def set_rigidity(self, level: int) -> bool:
        """
        Set rigidity level.
        
        Parameters
        ----------
        level : int
            Rigidity level (0-31)
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        ParameterOutOfRangeError
            If level out of range
        """
        self._check_connection()
        
        if not 0 <= level <= 31:
            raise ParameterOutOfRangeError('rigidity_level', level, 0, 31)
        
        return self._params.write('rigidity_level', level)
    
    def set_inertia_ratio(self, ratio: int) -> bool:
        """
        Set inertia ratio.
        
        Parameters
        ----------
        ratio : int
            Inertia ratio in percent
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.write('inertia_ratio', ratio)
    
    def auto_tune(self, mode: int = 1) -> bool:
        """
        Start auto-tuning.
        
        Parameters
        ----------
        mode : int
            Auto-tune mode:
            0 - Disabled
            1 - Standard auto-tuning
            2 - High inertia auto-tuning
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.write('auto_tune_mode', mode)
    
    # ==================== Status Monitoring ====================
    
    def get_status(self) -> ServoStatus:
        """
        Get servo status.
        
        Returns
        -------
        ServoStatus
            Current servo status
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._status
    
    def get_alarm(self) -> Optional[AlarmCode]:
        """
        Get current alarm code.
        
        Returns
        -------
        Optional[AlarmCode]
            Alarm code, None if failed
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._monitor.get_alarm()
    
    def get_alarm_description(self, alarm_code: Optional[int] = None) -> str:
        """
        Get alarm description.
        
        Parameters
        ----------
        alarm_code : Optional[int]
            Alarm code, uses current alarm if None
            
        Returns
        -------
        str
            Alarm description
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        
        if alarm_code is None:
            alarm_code = self.get_alarm()
        
        return ALARM_DESCRIPTIONS.get(
            alarm_code,
            f"Unknown alarm (0x{alarm_code:02X})"
        )
    
    def is_ready(self) -> bool:
        """
        Check if servo is ready for operation.
        
        Returns
        -------
        bool
            True if ready
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._monitor.is_servo_ready()
    
    def set_status_callback(self, callback: Optional[Callable]):
        """
        Set status change callback.
        
        Parameters
        ----------
        callback : Optional[Callable]
            Callback function(status_data: dict)
        """
        self._status_callback = callback
        if self._connected:
            self._monitor.set_status_callback(callback)
    
    def set_alarm_callback(self, callback: Optional[Callable]):
        """
        Set alarm callback.
        
        Parameters
        ----------
        callback : Optional[Callable]
            Callback function(alarm_code: int)
        """
        self._alarm_callback = callback
        if self._connected:
            self._monitor.set_alarm_callback(callback)
    
    # ==================== Servo Information ====================
    
    def _read_servo_info(self):
        """Read servo information from driver."""
        try:
            # TODO: Read actual servo info from parameters
            self._servo_info = ServoInfo(
                model="L7-400",
                firmware_version="2.10",
                serial_number="20250104001",
                rated_power=400.0,
                rated_torque=1.27,
                rated_speed=3000,
                max_speed=6000,
                encoder_resolution=131072
            )
        except Exception as e:
            logger.warning(f"Failed to read servo info: {e}")
    
    @property
    def info(self) -> ServoInfo:
        """Get servo information."""
        return self._servo_info
    
    # ==================== Context Manager ====================
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    # ==================== PR Control ====================
    
    def trigger_pr(self, path_id: int) -> bool:
        """
        Trigger PR path via direct register write (0x6002).
        
        Verified frames:
        - 0x0010 -> PR0, 0x0011 -> PR1 ... 0x0010 | path_id
        """
        self._check_connection()
        if not 0 <= path_id <= 15:
            raise InvalidPathError(path_id)
        return self._modbus.write_register(0x6002, 0x0010 | (path_id & 0x0F))
    
    def set_pr_path(self, path_id: int, position: int, speed: int, 
                   acceleration: int = 100, deceleration: int = 100,
                   delay: int = 0, s_curve: int = 0) -> bool:
        """
        Configure PR path.
        
        Parameters
        ----------
        path_id : int
            Path ID (0-15)
        position : int
            Target position in pulses
        speed : int
            Speed in RPM
        acceleration : int
            Acceleration time in ms/kRPM
        deceleration : int
            Deceleration time in ms/kRPM
        delay : int
            Delay time in ms
        s_curve : int
            S-curve time in ms
            
        Returns
        -------
        bool
            True if successful
        """
        from .motion import PRPath
        
        path = PRPath(
            path_id=path_id,
            position=position,
            speed=speed,
            acceleration=acceleration,
            deceleration=deceleration,
            delay=delay,
            s_curve=s_curve
        )
        
        return self._motion.set_pr_path(path)
    
    def stop_pr_motion(self) -> bool:
        """
        Stop PR motion.
        
        Returns
        -------
        bool
            True if successful
        """
        # Direct emergency stop via 0x6002 = 0x0040
        self._check_connection()
        return self._modbus.write_register(0x6002, 0x0040)
    
    def get_current_pr_path(self) -> Optional[int]:
        """
        Get currently executing PR path.
        
        Returns
        -------
        Optional[int]
            Current path ID or None
        """
        return self._motion.get_current_pr_path()
    
    def get_pr_position(self) -> Optional[int]:
        """
        Get current PR position.
        
        Returns
        -------
        Optional[int]
            PR position in pulses or None
        """
        return self._motion.get_pr_position()

    def get_pr_configured_position(self, path_id: int) -> Optional[int]:
        """
        获取指定PR路径配置的目标位置（指令单位，32位）。

        Parameters
        ----------
        path_id : int
            PR路径编号 (0-15)

        Returns
        -------
        Optional[int]
            目标位置（指令单位），或None表示读取失败
        """
        return self._motion.get_pr_configured_position(path_id)

    def get_control_operation(self) -> Optional[int]:
        """
        读取当前控制操作码（寄存器 0x6002）。
        用于显示最近一次PR/急停等控制写入的值。
        """
        self._check_connection()
        return self._modbus.read_register(0x6002)
    
    def is_pr_complete(self) -> bool:
        """
        Check if PR motion is complete.
        
        Returns
        -------
        bool
            True if complete
        """
        return self._motion.is_pr_complete()

    # ==================== Convenience getters for tests ====================

    def get_alarm_code(self) -> int:
        """Read raw alarm code register (0x0B1F)."""
        self._check_connection()
        value = self._params.read('alarm_code')
        return int(value) if value is not None else 0

    def get_digital_inputs(self) -> int:
        """Read DI status (0x0400)."""
        self._check_connection()
        value = self._params.read('di_status')
        return int(value) if value is not None else 0

    def get_digital_outputs(self) -> int:
        """Read DO status (0x0410)."""
        self._check_connection()
        value = self._params.read('do_status')
        return int(value) if value is not None else 0

    def get_temperature(self):
        """Read driver temperature (0x0B0B), returns Celsius as float if available."""
        self._check_connection()
        raw = self._params.read('driver_temperature')
        if raw is None:
            return None
        try:
            return float(raw) / 10.0
        except Exception:
            return None

    def get_servo_status(self) -> Optional[int]:
        """
        获取驱动器运行状态 (485地址0x0B05).
        
        Returns
        -------
        Optional[int]
            驱动器运行状态值，None表示读取失败
            
        Raises
        ------
        NotConnectedError
            If not connected
        """
        self._check_connection()
        return self._params.read('servo_status')

    def get_servo_status_description(self) -> str:
        """
        获取驱动器运行状态的描述信息.
        
        根据雷赛L7系列手册PAB.05参数定义：
        Bit 0: RDY - 伺服准备好
        Bit 1: RUN - 伺服运行
        Bit 2: ERR - 驱动器故障
        Bit 3: HOME_OK - 回零完成
        Bit 4: INP - 定位完成
        Bit 5: AT-SPEED - 速度到达
        Bit 6~15: 保留
        
        Returns
        -------
        str
            状态描述字符串
        """
        status = self.get_servo_status()
        if status is None:
            return "状态读取失败"
        
        status_bits = []
        
        if status & 0x0001:
            status_bits.append("伺服准备好(RDY)")
        if status & 0x0002:
            status_bits.append("伺服运行(RUN)")
        if status & 0x0004:
            status_bits.append("驱动器故障(ERR)")
        if status & 0x0008:
            status_bits.append("回零完成(HOME_OK)")
        if status & 0x0010:
            status_bits.append("定位完成(INP)")
        if status & 0x0020:
            status_bits.append("速度到达(AT-SPEED)")
        
        if not status_bits:
            return f"状态值: 0x{status:04X} (无特殊状态)"
        
        return f"状态值: 0x{status:04X} - {', '.join(status_bits)}"

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected else "disconnected"
        return f"L7Driver(port='{self._serial.port}', slave_id={self._modbus.slave_id}, status='{status}')"