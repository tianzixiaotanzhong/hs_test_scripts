"""
Modbus RTU protocol implementation.

This module provides a complete Modbus RTU implementation for communication
with Leisai L7 servo drivers.
"""

import struct
import time
import logging
from typing import Optional, List, Union, Tuple
from dataclasses import dataclass

from ..core.exceptions import (
    CommunicationError,
    ModbusError,
    TimeoutError
)
from ..core.constants import MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


@dataclass
class ModbusFrame:
    """Represents a Modbus RTU frame."""
    slave_id: int
    function_code: int
    data: bytes
    crc: Optional[int] = None
    
    def to_bytes(self) -> bytes:
        """Convert frame to bytes with CRC."""
        frame = struct.pack('BB', self.slave_id, self.function_code) + self.data
        if self.crc is None:
            self.crc = calculate_crc16(frame)
        return frame + struct.pack('<H', self.crc)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ModbusFrame':
        """Parse bytes into ModbusFrame."""
        if len(data) < 4:
            raise ValueError("Frame too short")
        
        slave_id = data[0]
        function_code = data[1]
        frame_data = data[2:-2]
        crc = struct.unpack('<H', data[-2:])[0]
        
        return cls(slave_id, function_code, frame_data, crc)


def calculate_crc16(data: bytes) -> int:
    """
    Calculate Modbus CRC16.
    
    Parameters
    ----------
    data : bytes
        Data to calculate CRC for
        
    Returns
    -------
    int
        CRC16 value
    """
    crc = 0xFFFF
    
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    
    return crc


class ModbusRTU:
    """
    Modbus RTU protocol handler.
    
    This class handles the low-level Modbus RTU protocol details including
    frame construction, CRC calculation, and error checking.
    """
    
    # Function codes
    READ_HOLDING_REGISTERS = 0x03
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_REGISTERS = 0x10
    
    def __init__(self, serial_connection):
        """
        Initialize Modbus RTU handler.
        
        Parameters
        ----------
        serial_connection : SerialConnection
            Serial connection to use for communication
        """
        self.serial = serial_connection
        self._transaction_id = 0
    
    def read_holding_registers(
        self, 
        slave_id: int,
        address: int,
        count: int = 1
    ) -> List[int]:
        """
        Read holding registers (function code 0x03).
        
        Parameters
        ----------
        slave_id : int
            Slave device ID
        address : int
            Starting register address
        count : int
            Number of registers to read
            
        Returns
        -------
        List[int]
            Register values
            
        Raises
        ------
        ModbusError
            If Modbus exception received
        CommunicationError
            If communication fails
        """
        # Build request
        data = struct.pack('>HH', address, count)
        request = ModbusFrame(slave_id, self.READ_HOLDING_REGISTERS, data)
        
        # Send and receive
        response = self._execute_transaction(request)
        
        # Parse response
        byte_count = response.data[0]
        if byte_count != count * 2:
            raise CommunicationError(f"Invalid byte count: {byte_count}")
        
        values = []
        for i in range(1, byte_count + 1, 2):
            value = struct.unpack('>H', response.data[i:i+2])[0]
            values.append(value)
        
        return values
    
    def write_single_register(
        self,
        slave_id: int,
        address: int,
        value: int
    ) -> bool:
        """
        Write single register (function code 0x06).
        
        Parameters
        ----------
        slave_id : int
            Slave device ID
        address : int
            Register address
        value : int
            Value to write
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        ModbusError
            If Modbus exception received
        CommunicationError
            If communication fails
        """
        # Build request
        data = struct.pack('>HH', address, value & 0xFFFF)
        request = ModbusFrame(slave_id, self.WRITE_SINGLE_REGISTER, data)
        
        # Send and receive
        response = self._execute_transaction(request)
        
        # Verify response
        resp_addr, resp_value = struct.unpack('>HH', response.data)
        if resp_addr != address or resp_value != (value & 0xFFFF):
            raise CommunicationError("Write verification failed")
        
        return True
    
    def write_multiple_registers(
        self,
        slave_id: int,
        address: int,
        values: List[int]
    ) -> bool:
        """
        Write multiple registers (function code 0x10).
        
        Parameters
        ----------
        slave_id : int
            Slave device ID
        address : int
            Starting register address  
        values : List[int]
            Values to write
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        ModbusError
            If Modbus exception received
        CommunicationError
            If communication fails
        """
        # Build request
        count = len(values)
        byte_count = count * 2
        
        data = struct.pack('>HHB', address, count, byte_count)
        for value in values:
            data += struct.pack('>H', value & 0xFFFF)
        
        request = ModbusFrame(slave_id, self.WRITE_MULTIPLE_REGISTERS, data)
        
        # Send and receive
        response = self._execute_transaction(request)
        
        # Verify response
        resp_addr, resp_count = struct.unpack('>HH', response.data)
        if resp_addr != address or resp_count != count:
            raise CommunicationError("Write verification failed")
        
        return True
    
    def _execute_transaction(self, request: ModbusFrame) -> ModbusFrame:
        """
        Execute a Modbus transaction with retry logic.
        
        Parameters
        ----------
        request : ModbusFrame
            Request frame to send
            
        Returns
        -------
        ModbusFrame
            Response frame
            
        Raises
        ------
        ModbusError
            If Modbus exception received
        CommunicationError
            If communication fails after retries
        """
        self._transaction_id += 1
        transaction_id = self._transaction_id
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Transaction {transaction_id} attempt {attempt + 1}")
                
                # Clear buffers
                self.serial.reset_buffers()
                
                # Send request
                request_bytes = request.to_bytes()
                logger.info(f"TX: {request_bytes.hex(' ').upper()}")
                self.serial.write(request_bytes)
                
                # Receive response
                response_bytes = self._receive_response(request.slave_id, request.function_code)
                logger.info(f"RX: {response_bytes.hex(' ').upper()}")
                
                # Parse response
                response = ModbusFrame.from_bytes(response_bytes)
                
                # Verify CRC
                calc_crc = calculate_crc16(response_bytes[:-2])
                if calc_crc != response.crc:
                    raise CommunicationError(f"CRC mismatch: {calc_crc:04X} != {response.crc:04X}")
                
                # Check for exception
                if response.function_code & 0x80:
                    exception_code = response.data[0]
                    raise ModbusError(exception_code)
                
                return response
                
            except TimeoutError:
                logger.warning(f"Transaction {transaction_id} timeout on attempt {attempt + 1}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                raise
            
            except Exception as e:
                logger.error(f"Transaction {transaction_id} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                raise
        
        raise CommunicationError(f"Transaction failed after {MAX_RETRIES} attempts")
    
    def _receive_response(self, slave_id: int, function_code: int) -> bytes:
        """
        Receive and validate response.
        
        Parameters
        ----------
        slave_id : int
            Expected slave ID
        function_code : int
            Expected function code (without error bit)
            
        Returns
        -------
        bytes
            Complete response frame
            
        Raises
        ------
        TimeoutError
            If response times out
        CommunicationError
            If response is invalid
        """
        # Read header (slave ID + function code)
        header = self.serial.read(2)
        if len(header) < 2:
            raise TimeoutError("Response timeout")
        
        recv_slave_id, recv_function = struct.unpack('BB', header)
        
        # Validate slave ID
        if recv_slave_id != slave_id:
            raise CommunicationError(f"Slave ID mismatch: {recv_slave_id} != {slave_id}")
        
        # Check if exception response
        if recv_function & 0x80:
            # Exception response: 1 byte exception code + 2 bytes CRC
            exception_data = self.serial.read(3)
            if len(exception_data) < 3:
                raise TimeoutError("Exception response incomplete")
            return header + exception_data
        
        # Normal response
        if recv_function != function_code:
            raise CommunicationError(f"Function code mismatch: {recv_function} != {function_code}")
        
        # Read rest of frame based on function code
        if function_code == self.READ_HOLDING_REGISTERS:
            # Byte count + data + CRC
            byte_count_data = self.serial.read(1)
            if not byte_count_data:
                raise TimeoutError("Byte count missing")
            
            byte_count = byte_count_data[0]
            data_and_crc = self.serial.read(byte_count + 2)
            if len(data_and_crc) < byte_count + 2:
                raise TimeoutError("Response data incomplete")
            
            return header + byte_count_data + data_and_crc
        
        elif function_code in [self.WRITE_SINGLE_REGISTER, self.WRITE_MULTIPLE_REGISTERS]:
            # Address (2) + value/count (2) + CRC (2)
            data = self.serial.read(6)
            if len(data) < 6:
                raise TimeoutError("Response data incomplete")
            return header + data
        
        else:
            raise CommunicationError(f"Unknown function code: {function_code}")


class ModbusClient:
    """
    High-level Modbus client for servo communication.
    
    This class provides a simplified interface for Modbus operations
    with automatic connection management and error handling.
    """
    
    def __init__(self, serial_connection, slave_id: int = 1):
        """
        Initialize Modbus client.
        
        Parameters
        ----------
        serial_connection : SerialConnection
            Serial connection to use
        slave_id : int
            Default slave ID
        """
        self.modbus = ModbusRTU(serial_connection)
        self.slave_id = slave_id
        self._cache = {}
        self._cache_timeout = 0.1  # 100ms cache
        
    def read_register(self, address: int, use_cache: bool = False) -> Optional[int]:
        """
        Read single register with optional caching.
        
        Parameters
        ----------
        address : int
            Register address
        use_cache : bool
            Whether to use cached value if available
            
        Returns
        -------
        Optional[int]
            Register value or None if failed
        """
        try:
            # Check cache
            if use_cache:
                cached = self._get_cached(address)
                if cached is not None:
                    return cached
            
            # Read from device
            values = self.modbus.read_holding_registers(self.slave_id, address, 1)
            value = values[0] if values else None
            
            # Update cache
            if value is not None:
                self._set_cached(address, value)
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to read register 0x{address:04X}: {e}")
            return None
    
    def write_register(self, address: int, value: int) -> bool:
        """
        Write single register.
        
        Parameters
        ----------
        address : int
            Register address
        value : int
            Value to write
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            success = self.modbus.write_single_register(self.slave_id, address, value)
            
            # Invalidate cache
            if success:
                self._invalidate_cache(address)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to write register 0x{address:04X}: {e}")
            return False
    
    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        Read multiple registers.
        
        Parameters
        ----------
        address : int
            Starting address
        count : int
            Number of registers
            
        Returns
        -------
        Optional[List[int]]
            Register values or None if failed
        """
        try:
            return self.modbus.read_holding_registers(self.slave_id, address, count)
        except Exception as e:
            logger.error(f"Failed to read {count} registers from 0x{address:04X}: {e}")
            return None
    
    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        Write multiple registers.
        
        Parameters
        ----------
        address : int
            Starting address
        values : List[int]
            Values to write
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            success = self.modbus.write_multiple_registers(self.slave_id, address, values)
            
            # Invalidate cache
            if success:
                for i in range(len(values)):
                    self._invalidate_cache(address + i)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to write {len(values)} registers to 0x{address:04X}: {e}")
            return False
    
    def read_32bit(self, address: int) -> Optional[int]:
        """
        Read 32-bit value from two consecutive registers.
        
        Parameters
        ----------
        address : int
            Starting address
            
        Returns
        -------
        Optional[int]
            32-bit value or None if failed
        """
        values = self.read_registers(address, 2)
        if values and len(values) == 2:
            value = (values[1] << 16) | values[0]
            # Handle sign extension
            if value & 0x80000000:
                value = value - 0x100000000
            return value
        return None
    
    def write_32bit(self, address: int, value: int) -> bool:
        """
        Write 32-bit value to two consecutive registers.
        
        Parameters
        ----------
        address : int
            Starting address
        value : int
            32-bit value to write
            
        Returns
        -------
        bool
            True if successful
        """
        # Split into two 16-bit values
        low = value & 0xFFFF
        high = (value >> 16) & 0xFFFF
        return self.write_registers(address, [low, high])
    
    def _get_cached(self, address: int) -> Optional[int]:
        """Get cached value if not expired."""
        if address in self._cache:
            value, timestamp = self._cache[address]
            if time.time() - timestamp < self._cache_timeout:
                return value
        return None
    
    def _set_cached(self, address: int, value: int):
        """Store value in cache."""
        self._cache[address] = (value, time.time())
    
    def _invalidate_cache(self, address: int = None):
        """Invalidate cache for address or all."""
        if address is None:
            self._cache.clear()
        else:
            self._cache.pop(address, None)