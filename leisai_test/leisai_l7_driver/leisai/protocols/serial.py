"""
Serial communication layer.

This module provides the serial communication interface for the Modbus protocol.
"""

import serial
import time
import logging
from typing import Optional, Union
from threading import Lock

from ..core.exceptions import ConnectionError, TimeoutError, CommunicationError
from ..core.constants import DEFAULT_BAUDRATE, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


class SerialConnection:
    """
    Thread-safe serial connection handler.
    
    This class manages the serial port connection and provides
    thread-safe read/write operations.
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
        **kwargs
    ):
        """
        Initialize serial connection.
        
        Parameters
        ----------
        port : str
            Serial port name (e.g., 'COM3' or '/dev/ttyUSB0')
        baudrate : int
            Baud rate (default: 38400)
        timeout : float
            Read timeout in seconds (default: 1.0)
        **kwargs
            Additional arguments passed to serial.Serial
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_args = {
            'bytesize': kwargs.get('bytesize', serial.EIGHTBITS),
            'parity': kwargs.get('parity', serial.PARITY_NONE),
            'stopbits': kwargs.get('stopbits', serial.STOPBITS_ONE),
            'xonxoff': kwargs.get('xonxoff', False),
            'rtscts': kwargs.get('rtscts', False),
            'dsrdtr': kwargs.get('dsrdtr', False),
            'inter_byte_timeout': kwargs.get('inter_byte_timeout', None),
            'write_timeout': kwargs.get('write_timeout', None),
        }
        
        self._serial: Optional[serial.Serial] = None
        self._lock = Lock()
        self._connected = False
        
    @property
    def is_connected(self) -> bool:
        """Check if serial port is connected and open."""
        return self._connected and self._serial and self._serial.is_open
    
    def connect(self) -> bool:
        """
        Open serial connection.
        
        Returns
        -------
        bool
            True if connection successful
            
        Raises
        ------
        ConnectionError
            If connection fails
        """
        with self._lock:
            if self.is_connected:
                logger.debug(f"Already connected to {self.port}")
                return True
            
            try:
                logger.info(f"Opening serial port {self.port} at {self.baudrate} baud")
                
                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    **self.serial_args
                )
                
                # Clear buffers
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
                
                self._connected = True
                logger.info(f"Serial port {self.port} opened successfully")
                return True
                
            except serial.SerialException as e:
                logger.error(f"Failed to open serial port {self.port}: {e}")
                raise ConnectionError(f"Cannot open serial port {self.port}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error opening serial port: {e}")
                raise ConnectionError(f"Serial connection failed: {e}")
    
    def disconnect(self):
        """Close serial connection."""
        with self._lock:
            if self._serial:
                try:
                    if self._serial.is_open:
                        # Flush buffers before closing
                        self._serial.flush()
                        self._serial.close()
                    logger.info(f"Serial port {self.port} closed")
                except Exception as e:
                    logger.warning(f"Error closing serial port: {e}")
                finally:
                    self._serial = None
                    self._connected = False
    
    def write(self, data: bytes) -> int:
        """
        Write data to serial port.
        
        Parameters
        ----------
        data : bytes
            Data to write
            
        Returns
        -------
        int
            Number of bytes written
            
        Raises
        ------
        CommunicationError
            If write fails
        """
        if not self.is_connected:
            raise CommunicationError("Serial port not connected")
        
        with self._lock:
            try:
                bytes_written = self._serial.write(data)
                self._serial.flush()  # Ensure data is sent
                return bytes_written
            except serial.SerialTimeoutException:
                raise TimeoutError("Serial write timeout")
            except serial.SerialException as e:
                self._connected = False
                raise CommunicationError(f"Serial write error: {e}")
    
    def read(self, size: int = 1) -> bytes:
        """
        Read data from serial port.
        
        Parameters
        ----------
        size : int
            Number of bytes to read
            
        Returns
        -------
        bytes
            Data read (may be less than size if timeout)
            
        Raises
        ------
        TimeoutError
            If no data received within timeout
        CommunicationError
            If read fails
        """
        if not self.is_connected:
            raise CommunicationError("Serial port not connected")
        
        with self._lock:
            try:
                data = self._serial.read(size)
                if not data and size > 0:
                    raise TimeoutError("Serial read timeout")
                return data
            except serial.SerialException as e:
                self._connected = False
                raise CommunicationError(f"Serial read error: {e}")
    
    def read_until(self, terminator: bytes = b'\n', size: Optional[int] = None) -> bytes:
        """
        Read data until terminator is found.
        
        Parameters
        ----------
        terminator : bytes
            Terminator sequence
        size : Optional[int]
            Maximum number of bytes to read
            
        Returns
        -------
        bytes
            Data read including terminator
            
        Raises
        ------
        TimeoutError
            If terminator not found within timeout
        CommunicationError
            If read fails
        """
        if not self.is_connected:
            raise CommunicationError("Serial port not connected")
        
        with self._lock:
            try:
                data = self._serial.read_until(terminator, size)
                if not data:
                    raise TimeoutError("Serial read timeout")
                return data
            except serial.SerialException as e:
                self._connected = False
                raise CommunicationError(f"Serial read error: {e}")
    
    def in_waiting(self) -> int:
        """
        Get number of bytes in receive buffer.
        
        Returns
        -------
        int
            Number of bytes waiting
        """
        if not self.is_connected:
            return 0
        
        with self._lock:
            try:
                return self._serial.in_waiting
            except:
                return 0
    
    def reset_buffers(self):
        """Clear input and output buffers."""
        if not self.is_connected:
            return
        
        with self._lock:
            try:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
            except Exception as e:
                logger.warning(f"Failed to reset buffers: {e}")
    
    def set_timeout(self, timeout: float):
        """
        Set read timeout.
        
        Parameters
        ----------
        timeout : float
            Timeout in seconds
        """
        self.timeout = timeout
        if self._serial:
            with self._lock:
                self._serial.timeout = timeout
    
    def set_baudrate(self, baudrate: int):
        """
        Change baudrate.
        
        Parameters
        ----------
        baudrate : int
            New baudrate
            
        Note
        ----
        This will briefly disconnect and reconnect the port.
        """
        if not self.is_connected:
            self.baudrate = baudrate
            return
        
        with self._lock:
            try:
                self._serial.baudrate = baudrate
                self.baudrate = baudrate
                logger.info(f"Baudrate changed to {baudrate}")
            except Exception as e:
                logger.error(f"Failed to change baudrate: {e}")
                raise CommunicationError(f"Cannot change baudrate: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected else "disconnected"
        return f"SerialConnection(port='{self.port}', baudrate={self.baudrate}, status='{status}')"