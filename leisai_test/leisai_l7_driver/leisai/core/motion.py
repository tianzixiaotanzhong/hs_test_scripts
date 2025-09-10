"""
Motion control for L7 servo drivers.

This module provides motion control functionality including position,
speed, torque control, and PR path control.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from .constants import (
    PR_PATH_BASE, PR_PATH_SIZE,
    HomingMode, MAX_SPEED_RPM, MAX_POSITION
)
from .exceptions import (
    InvalidPathError, MotionError,
    ParameterOutOfRangeError
)

logger = logging.getLogger(__name__)


@dataclass
class PRPath:
    """PR path configuration."""
    path_id: int
    position: int
    speed: int
    acceleration: int
    deceleration: int
    delay: int = 0
    s_curve: int = 0
    
    def validate(self):
        """Validate path parameters."""
        if not 0 <= self.path_id <= 15:
            raise InvalidPathError(self.path_id)
        
        if not MIN_POSITION <= self.position <= MAX_POSITION:
            raise ParameterOutOfRangeError(
                'position', self.position, MIN_POSITION, MAX_POSITION
            )
        
        if not 0 <= self.speed <= MAX_SPEED_RPM:
            raise ParameterOutOfRangeError(
                'speed', self.speed, 0, MAX_SPEED_RPM
            )


class MotionController:
    """
    Motion controller for L7 servo.
    
    This class provides methods for controlling servo motion including
    position, speed, torque control, and PR path execution.
    """
    
    def __init__(self, modbus_client, param_manager):
        """
        Initialize motion controller.
        
        Parameters
        ----------
        modbus_client : ModbusClient
            Modbus client for communication
        param_manager : ParameterManager
            Parameter manager
        """
        self._modbus = modbus_client
        self._params = param_manager
    
    # ==================== Basic Motion ====================
    
    def get_position(self) -> Optional[int]:
        """
        Get current position in pulses.
        
        Returns
        -------
        Optional[int]
            Current position or None if failed
        """
        return self._params.read('encoder_position')
    
    def get_command_position(self) -> Optional[int]:
        """
        Get commanded position in pulses.
        
        Returns
        -------
        Optional[int]
            Command position or None if failed
        """
        return self._params.read('command_position')
    
    def get_position_error(self) -> Optional[int]:
        """
        Get position error in pulses.
        
        Returns
        -------
        Optional[int]
            Position error or None if failed
        """
        return self._params.read('position_error')
    
    def get_speed(self) -> Optional[int]:
        """
        Get current speed in rpm.
        
        Returns
        -------
        Optional[int]
            Current speed or None if failed
        """
        return self._params.read('motor_speed')
    
    def get_torque(self) -> Optional[int]:
        """
        Get current torque percentage.
        
        Returns
        -------
        Optional[int]
            Torque percentage or None if failed
        """
        return self._params.read('torque_feedback')
    
    def set_speed_command(self, speed: int) -> bool:
        """
        Set speed command.
        
        Parameters
        ----------
        speed : int
            Target speed in rpm
            
        Returns
        -------
        bool
            True if successful
        """
        logger.info(f"Setting speed command: {speed} rpm")
        return self._params.write('speed_command_1', speed)
    
    def set_torque_limit(self, limit: int) -> bool:
        """
        Set torque limit.
        
        Parameters
        ----------
        limit : int
            Torque limit percentage (0-300%)
            
        Returns
        -------
        bool
            True if successful
        """
        if not 0 <= limit <= 300:
            raise ParameterOutOfRangeError('torque_limit', limit, 0, 300)
        
        logger.info(f"Setting torque limit: {limit}%")
        return self._params.write('torque_limit_1', limit)
    
    def set_acceleration(self, acc_time: int, dec_time: int) -> bool:
        """
        Set acceleration and deceleration time.
        
        Parameters
        ----------
        acc_time : int
            Acceleration time in ms
        dec_time : int
            Deceleration time in ms
            
        Returns
        -------
        bool
            True if successful
        """
        logger.info(f"Setting acceleration: {acc_time}ms, deceleration: {dec_time}ms")
        
        success = self._params.write('acceleration_time', acc_time)
        if success:
            success = self._params.write('deceleration_time', dec_time)
        
        return success
    
    # ==================== JOG Control ====================
    
    def jog(self, speed: int, direction: bool = True) -> bool:
        """
        Start JOG motion.
        
        Parameters
        ----------
        speed : int
            JOG speed in rpm
        direction : bool
            True for forward, False for reverse
            
        Returns
        -------
        bool
            True if successful
        """
        logger.info(f"Starting JOG: {speed} rpm, {'forward' if direction else 'reverse'}")
        
        # Set JOG speed with direction
        jog_speed = speed if direction else -speed
        success = self._params.write('pr_jog_speed', jog_speed)
        
        if success:
            # Trigger JOG via PR control register
            pr_control = self._params.read('pr_control') or 0
            pr_control |= 0x0002  # Set JOG trigger bit
            success = self._params.write('pr_control', pr_control)
        
        return success
    
    def stop_jog(self) -> bool:
        """
        Stop JOG motion.
        
        Returns
        -------
        bool
            True if successful
        """
        logger.info("Stopping JOG")
        
        # Clear JOG trigger bit
        pr_control = self._params.read('pr_control') or 0
        pr_control &= ~0x0002
        return self._params.write('pr_control', pr_control)
    
    # ==================== Homing ====================
    
    def home(self, mode: int = 0, high_speed: int = 500, low_speed: int = 50) -> bool:
        """
        Start homing sequence.
        
        Parameters
        ----------
        mode : int
            Homing mode (see HomingMode enum)
        high_speed : int
            High speed in rpm
        low_speed : int
            Low speed in rpm
            
        Returns
        -------
        bool
            True if successful
        """
        logger.info(f"Starting homing: mode={mode}, high={high_speed}rpm, low={low_speed}rpm")
        
        # Set homing parameters
        success = self._params.write('pr_home_mode', mode)
        if success:
            success = self._params.write('pr_home_speed_high', high_speed)
        if success:
            success = self._params.write('pr_home_speed_low', low_speed)
        
        # Trigger homing
        if success:
            pr_control = self._params.read('pr_control') or 0
            pr_control |= 0x0001  # Set homing trigger bit
            success = self._params.write('pr_control', pr_control)
        
        return success
    
    def set_home_offset(self, offset: int) -> bool:
        """
        Set homing offset.
        
        Parameters
        ----------
        offset : int
            Offset in pulses
            
        Returns
        -------
        bool
            True if successful
        """
        logger.info(f"Setting home offset: {offset} pulses")
        return self._params.write('pr_home_offset', offset)
    
    def is_homing_complete(self) -> bool:
        """
        Check if homing is complete.
        
        Returns
        -------
        bool
            True if homing complete
        """
        status = self._params.read('pr_status')
        if status is not None:
            # Check homing complete bit
            return bool(status & 0x0001)
        return False
    
    # ==================== PR Path Control ====================
    
    def set_pr_path(self, path: PRPath) -> bool:
        """
        Configure PR path.
        
        Parameters
        ----------
        path : PRPath
            Path configuration
            
        Returns
        -------
        bool
            True if successful
        """
        # Validate path
        path.validate()
        
        logger.info(f"Setting PR path {path.path_id}")
        
        # Calculate register addresses
        base_addr = PR_PATH_BASE + (path.path_id * PR_PATH_SIZE)
        
        # Prepare path data
        values = [
            path.position & 0xFFFF,           # Position low
            (path.position >> 16) & 0xFFFF,   # Position high
            path.speed,                       # Speed
            0,                                # Reserved
            path.acceleration,                # Acceleration
            path.deceleration,                # Deceleration
            path.delay,                       # Delay
            path.s_curve,                     # S-curve
        ]
        
        # Write path data
        return self._modbus.write_registers(base_addr, values)
    
    def execute_pr_path(self, path_id: int) -> bool:
        """
        Execute PR path.
        
        Parameters
        ----------
        path_id : int
            Path ID (0-15)
            
        Returns
        -------
        bool
            True if successful
        """
        if not 0 <= path_id <= 15:
            raise InvalidPathError(path_id)
        
        logger.info(f"Executing PR path {path_id}")
        
        # Set path ID and trigger execution
        pr_control = self._params.read('pr_control') or 0
        pr_control = (pr_control & 0xFF00) | (path_id << 4) | 0x0004
        return self._params.write('pr_control', pr_control)
    
    def stop_pr_motion(self) -> bool:
        """
        Stop PR motion.
        
        Returns
        -------
        bool
            True if successful
        """
        logger.info("Stopping PR motion")
        
        # Clear all trigger bits
        pr_control = self._params.read('pr_control') or 0
        pr_control &= 0xFF00
        return self._params.write('pr_control', pr_control)
    
    def get_current_pr_path(self) -> Optional[int]:
        """
        Get currently executing PR path.
        
        Returns
        -------
        Optional[int]
            Current path ID or None
        """
        return self._params.read('pr_current_path')
    
    def get_pr_position(self) -> Optional[int]:
        """
        Get current PR position.
        
        Returns
        -------
        Optional[int]
            PR position in pulses or None
        """
        return self._params.read('pr_current_position')
    
    def is_pr_complete(self) -> bool:
        """
        Check if PR motion is complete.
        
        Returns
        -------
        bool
            True if complete
        """
        status = self._params.read('pr_status')
        if status is not None:
            # Check PR complete bit
            return bool(status & 0x0002)
        return False