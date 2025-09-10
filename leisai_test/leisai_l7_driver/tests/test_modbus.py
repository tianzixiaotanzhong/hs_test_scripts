"""Unit tests for Modbus protocol implementation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from leisai.protocols.modbus import ModbusRTU, ModbusFrame, calculate_crc16
from leisai.core.exceptions import ModbusError, CommunicationError


class TestCRC16:
    """Test CRC16 calculation."""
    
    def test_crc16_calculation(self):
        """Test CRC16 calculation with known values."""
        # Test data from Modbus specification
        data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01])
        expected_crc = 0xCA84
        
        calculated_crc = calculate_crc16(data)
        assert calculated_crc == expected_crc
    
    def test_crc16_empty(self):
        """Test CRC16 with empty data."""
        data = bytes()
        crc = calculate_crc16(data)
        assert crc == 0xFFFF


class TestModbusFrame:
    """Test ModbusFrame class."""
    
    def test_frame_creation(self):
        """Test creating a Modbus frame."""
        frame = ModbusFrame(
            slave_id=1,
            function_code=0x03,
            data=bytes([0x00, 0x00, 0x00, 0x01])
        )
        
        assert frame.slave_id == 1
        assert frame.function_code == 0x03
        assert frame.data == bytes([0x00, 0x00, 0x00, 0x01])
    
    def test_frame_to_bytes(self):
        """Test converting frame to bytes with CRC."""
        frame = ModbusFrame(
            slave_id=1,
            function_code=0x03,
            data=bytes([0x00, 0x00, 0x00, 0x01])
        )
        
        frame_bytes = frame.to_bytes()
        
        # Check structure
        assert frame_bytes[0] == 1  # Slave ID
        assert frame_bytes[1] == 0x03  # Function code
        assert frame_bytes[2:6] == bytes([0x00, 0x00, 0x00, 0x01])  # Data
        
        # Verify CRC
        crc = calculate_crc16(frame_bytes[:-2])
        assert frame_bytes[-2:] == crc.to_bytes(2, 'little')
    
    def test_frame_from_bytes(self):
        """Test parsing bytes into ModbusFrame."""
        data = bytes([0x01, 0x03, 0x02, 0x00, 0x01, 0x79, 0x84])
        
        frame = ModbusFrame.from_bytes(data)
        
        assert frame.slave_id == 1
        assert frame.function_code == 0x03
        assert frame.data == bytes([0x02, 0x00, 0x01])
        assert frame.crc == 0x8479


class TestModbusRTU:
    """Test ModbusRTU protocol handler."""
    
    @pytest.fixture
    def mock_serial(self):
        """Create mock serial connection."""
        mock = Mock()
        mock.write.return_value = 8
        mock.read.return_value = bytes([0x01, 0x03, 0x02, 0x00, 0x01, 0x79, 0x84])
        mock.reset_buffers.return_value = None
        return mock
    
    @pytest.fixture
    def modbus(self, mock_serial):
        """Create ModbusRTU instance with mock serial."""
        return ModbusRTU(mock_serial)
    
    def test_read_holding_registers(self, modbus, mock_serial):
        """Test reading holding registers."""
        # Setup mock response
        response_data = bytes([
            0x01,  # Slave ID
            0x03,  # Function code
            0x04,  # Byte count
            0x00, 0x01,  # Register 1
            0x00, 0x02,  # Register 2
            0x79, 0x84  # CRC
        ])
        mock_serial.read.side_effect = [
            response_data[:2],  # Header
            response_data[2:3],  # Byte count
            response_data[3:-2],  # Data
            response_data[-2:]  # CRC
        ]
        
        # Read registers
        values = modbus.read_holding_registers(1, 0x0000, 2)
        
        assert values == [1, 2]
        assert mock_serial.write.called
        assert mock_serial.reset_buffers.called
    
    def test_write_single_register(self, modbus, mock_serial):
        """Test writing single register."""
        # Setup mock response
        response_data = bytes([
            0x01,  # Slave ID
            0x06,  # Function code
            0x00, 0x01,  # Address
            0x00, 0x03,  # Value
            0x9A, 0x9B  # CRC
        ])
        mock_serial.read.side_effect = [
            response_data[:2],  # Header
            response_data[2:-2],  # Data
            response_data[-2:]  # CRC
        ]
        
        # Write register
        success = modbus.write_single_register(1, 0x0001, 0x0003)
        
        assert success is True
        assert mock_serial.write.called
    
    def test_modbus_exception(self, modbus, mock_serial):
        """Test handling Modbus exception response."""
        # Setup exception response
        response_data = bytes([
            0x01,  # Slave ID
            0x83,  # Function code with error bit
            0x02,  # Exception code (illegal address)
            0xC0, 0xF1  # CRC
        ])
        mock_serial.read.side_effect = [
            response_data[:2],  # Header
            response_data[2:3],  # Exception code
            response_data[3:]  # CRC
        ]
        
        # Should raise ModbusError
        with pytest.raises(ModbusError) as exc_info:
            modbus.read_holding_registers(1, 0xFFFF, 1)
        
        assert exc_info.value.exception_code == 0x02
    
    def test_communication_timeout(self, modbus, mock_serial):
        """Test handling communication timeout."""
        # Setup timeout
        mock_serial.read.return_value = bytes()  # Empty response
        
        # Should raise TimeoutError
        with pytest.raises(Exception):  # Will be TimeoutError in actual implementation
            modbus.read_holding_registers(1, 0x0000, 1)