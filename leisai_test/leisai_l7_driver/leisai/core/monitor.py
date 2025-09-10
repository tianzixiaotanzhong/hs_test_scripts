"""
Status monitoring for L7 servo drivers.

This module provides real-time status monitoring and alarm handling.
"""

import logging
import time
from typing import Optional, Callable, Dict, Any
from threading import Thread, Event

from .constants import AlarmCode, DISignal, DOSignal
from .exceptions import AlarmError

logger = logging.getLogger(__name__)


class StatusMonitor:
    """
    Status monitor for L7 servo.
    
    This class provides real-time monitoring of servo status,
    alarms, and I/O signals with callback support.
    """
    
    def __init__(self, modbus_client, param_manager):
        """
        Initialize status monitor.
        
        Parameters
        ----------
        modbus_client : ModbusClient
            Modbus client for communication
        param_manager : ParameterManager
            Parameter manager
        """
        self._modbus = modbus_client
        self._params = param_manager
        
        # Monitoring state
        self._monitor_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._monitor_interval = 0.1
        
        # Callbacks
        self._status_callback: Optional[Callable] = None
        self._alarm_callback: Optional[Callable] = None
        
        # Last known state
        self._last_alarm: Optional[int] = None
        self._last_position: Optional[int] = None
        self._last_speed: Optional[int] = None
        self._last_torque: Optional[int] = None
    
    def start(
        self,
        interval: float = 0.1,
        status_callback: Optional[Callable] = None,
        alarm_callback: Optional[Callable] = None
    ):
        """
        Start status monitoring.
        
        Parameters
        ----------
        interval : float
            Monitoring interval in seconds
        status_callback : Optional[Callable]
            Callback for status changes
        alarm_callback : Optional[Callable]
            Callback for alarm changes
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Monitoring already running")
            return
        
        self._monitor_interval = interval
        self._status_callback = status_callback
        self._alarm_callback = alarm_callback
        
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info(f"Status monitoring started (interval: {interval}s)")
    
    def stop(self):
        """Stop status monitoring."""
        if not self._monitor_thread:
            return
        
        self._stop_event.set()
        self._monitor_thread.join(timeout=2.0)
        self._monitor_thread = None
        
        logger.info("Status monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Read current status
                status_data = self._read_status()
                
                # Check for changes
                self._check_alarm_change(status_data.get('alarm'))
                self._check_status_change(status_data)
                
                # Wait for next interval
                self._stop_event.wait(self._monitor_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                self._stop_event.wait(1.0)
    
    def _read_status(self) -> Dict[str, Any]:
        """Read current status from servo."""
        status = {}
        
        # Read key parameters
        status['alarm'] = self._params.read('alarm_code')
        status['position'] = self._params.read('encoder_position')
        status['speed'] = self._params.read('motor_speed')
        status['torque'] = self._params.read('torque_feedback')
        status['di_status'] = self._params.read('di_status')
        status['do_status'] = self._params.read('do_status')
        status['bus_voltage'] = self._params.read('dc_bus_voltage')
        status['temperature'] = self._params.read('driver_temperature')
        
        return status
    
    def _check_alarm_change(self, alarm: Optional[int]):
        """Check for alarm changes."""
        if alarm is None:
            return
        
        if alarm != self._last_alarm:
            self._last_alarm = alarm
            
            if self._alarm_callback:
                try:
                    self._alarm_callback(alarm)
                except Exception as e:
                    logger.error(f"Alarm callback error: {e}")
            
            if alarm != AlarmCode.NO_ALARM:
                logger.warning(f"Alarm active: 0x{alarm:02X}")
    
    def _check_status_change(self, status: Dict[str, Any]):
        """Check for status changes."""
        # Check for significant changes
        changed = False
        
        if status.get('position') != self._last_position:
            self._last_position = status.get('position')
            changed = True
        
        if status.get('speed') != self._last_speed:
            self._last_speed = status.get('speed')
            changed = True
        
        if status.get('torque') != self._last_torque:
            self._last_torque = status.get('torque')
            changed = True
        
        # Call status callback if changed
        if changed and self._status_callback:
            try:
                self._status_callback(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    # ==================== Status Queries ====================
    
    def get_alarm(self) -> Optional[AlarmCode]:
        """
        Get current alarm code.
        
        Returns
        -------
        Optional[AlarmCode]
            Alarm code or None if failed
        """
        alarm = self._params.read('alarm_code')
        if alarm is not None:
            # 0xFFDC (65500) appears to indicate no alarm
            if alarm == 0xFFDC or alarm == 65500:
                return AlarmCode.NO_ALARM
            try:
                return AlarmCode(alarm)
            except ValueError:
                # Unknown alarm code
                return alarm
        return None
    
    def is_servo_ready(self) -> bool:
        """
        Check if servo is ready.
        
        Returns
        -------
        bool
            True if ready
        """
        # Check alarm
        alarm = self.get_alarm()
        if alarm and alarm != AlarmCode.NO_ALARM:
            return False
        
        # Check S-RDY signal
        do_status = self._params.read('do_status')
        if do_status is not None:
            return bool(do_status & DOSignal.DO1_SRDY)
        
        return False
    
    def is_in_position(self) -> bool:
        """
        Check if servo is in position.
        
        Returns
        -------
        bool
            True if in position
        """
        do_status = self._params.read('do_status')
        if do_status is not None:
            return bool(do_status & DOSignal.DO2_INP)
        return False
    
    def is_at_speed(self) -> bool:
        """
        Check if servo is at target speed.
        
        Returns
        -------
        bool
            True if at speed
        """
        do_status = self._params.read('do_status')
        if do_status is not None:
            return bool(do_status & DOSignal.DO5_ATSPD)
        return False
    
    def is_torque_limited(self) -> bool:
        """
        Check if servo is torque limited.
        
        Returns
        -------
        bool
            True if torque limited
        """
        do_status = self._params.read('do_status')
        if do_status is not None:
            return bool(do_status & DOSignal.DO4_ATLMT)
        return False
    
    def get_di_status(self) -> Optional[int]:
        """
        Get digital input status.
        
        Returns
        -------
        Optional[int]
            DI status bitmap or None
        """
        return self._params.read('di_status')
    
    def get_do_status(self) -> Optional[int]:
        """
        Get digital output status.
        
        Returns
        -------
        Optional[int]
            DO status bitmap or None
        """
        return self._params.read('do_status')
    
    def check_di_signal(self, signal: DISignal) -> bool:
        """
        Check specific DI signal.
        
        Parameters
        ----------
        signal : DISignal
            Signal to check
            
        Returns
        -------
        bool
            True if signal is active
        """
        di_status = self.get_di_status()
        if di_status is not None:
            return bool(di_status & signal)
        return False
    
    def check_do_signal(self, signal: DOSignal) -> bool:
        """
        Check specific DO signal.
        
        Parameters
        ----------
        signal : DOSignal
            Signal to check
            
        Returns
        -------
        bool
            True if signal is active
        """
        do_status = self.get_do_status()
        if do_status is not None:
            return bool(do_status & signal)
        return False
    
    def get_bus_voltage(self) -> Optional[float]:
        """
        Get DC bus voltage.
        
        Returns
        -------
        Optional[float]
            Bus voltage in V or None
        """
        value = self._params.read('dc_bus_voltage')
        if value is not None:
            return value / 10.0  # Convert to volts
        return None
    
    def get_temperature(self) -> Optional[float]:
        """
        Get driver temperature.
        
        Returns
        -------
        Optional[float]
            Temperature in °C or None
        """
        value = self._params.read('driver_temperature')
        if value is not None:
            return value / 10.0  # Convert to Celsius
        return None
    
    def set_status_callback(self, callback: Optional[Callable]):
        """Set status change callback."""
        self._status_callback = callback
    
    def set_alarm_callback(self, callback: Optional[Callable]):
        """Set alarm change callback."""
        self._alarm_callback = callback