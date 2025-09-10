"""
Parameter management for L7 servo drivers.

This module handles parameter reading, writing, and management.
"""

import json
import logging
from typing import Optional, Any, Dict, List
from pathlib import Path

from .constants import PARAMETER_ADDRESS
from .exceptions import ParameterError, InvalidParameterError

logger = logging.getLogger(__name__)


class ParameterManager:
    """
    Manages servo parameters.
    
    This class provides methods for reading, writing, and managing
    servo parameters with validation and caching.
    """
    
    def __init__(self, modbus_client):
        """
        Initialize parameter manager.
        
        Parameters
        ----------
        modbus_client : ModbusClient
            Modbus client for communication
        """
        self._modbus = modbus_client
        self._cache = {}
        self._modified = set()
    
    def read(self, name: str, use_cache: bool = False) -> Optional[Any]:
        """
        Read parameter by name.
        
        Parameters
        ----------
        name : str
            Parameter name
        use_cache : bool
            Use cached value if available
            
        Returns
        -------
        Optional[Any]
            Parameter value or None if failed
            
        Raises
        ------
        InvalidParameterError
            If parameter name is invalid
        """
        if name not in PARAMETER_ADDRESS:
            raise InvalidParameterError(name, message=f"Unknown parameter: {name}")
        
        # Check cache
        if use_cache and name in self._cache:
            return self._cache[name]
        
        # Read from device
        address = PARAMETER_ADDRESS[name]
        
        # Handle 32-bit parameters
        if name in ['encoder_position', 'command_position', 'motor_position_cmd_unit', 'pr_current_position', 'pr_home_offset']:
            value = self._read_32bit(address)
        else:
            value = self._modbus.read_register(address)
        
        # Update cache
        if value is not None:
            self._cache[name] = value
        
        return value
    
    def write(self, name: str, value: Any) -> bool:
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
        InvalidParameterError
            If parameter name is invalid
        """
        if name not in PARAMETER_ADDRESS:
            raise InvalidParameterError(name, message=f"Unknown parameter: {name}")
        
        address = PARAMETER_ADDRESS[name]
        
        # Handle 32-bit parameters
        if name in ['encoder_position', 'command_position', 'motor_position_cmd_unit', 'pr_current_position', 'pr_home_offset']:
            success = self._write_32bit(address, value)
        else:
            success = self._modbus.write_register(address, value)
        
        if success:
            self._cache[name] = value
            self._modified.add(name)
        
        return success
    
    def read_multiple(self, names: List[str]) -> Dict[str, Any]:
        """
        Read multiple parameters.
        
        Parameters
        ----------
        names : List[str]
            Parameter names
            
        Returns
        -------
        Dict[str, Any]
            Parameter values
        """
        values = {}
        for name in names:
            try:
                values[name] = self.read(name)
            except Exception as e:
                logger.warning(f"Failed to read {name}: {e}")
                values[name] = None
        return values
    
    def write_multiple(self, parameters: Dict[str, Any]) -> Dict[str, bool]:
        """
        Write multiple parameters.
        
        Parameters
        ----------
        parameters : Dict[str, Any]
            Parameter name-value pairs
            
        Returns
        -------
        Dict[str, bool]
            Success status for each parameter
        """
        results = {}
        for name, value in parameters.items():
            try:
                results[name] = self.write(name, value)
            except Exception as e:
                logger.warning(f"Failed to write {name}: {e}")
                results[name] = False
        return results
    
    def _read_32bit(self, address: int) -> Optional[int]:
        """Read 32-bit value from two registers."""
        values = self._modbus.read_registers(address, 2)
        if values and len(values) == 2:
            # Combine low and high words (little-endian)
            value = (values[1] << 16) | values[0]
            # For position values, treat as signed 32-bit integer
            if value & 0x80000000:
                value = value - 0x100000000
            return value
        return None
    
    def _write_32bit(self, address: int, value: int) -> bool:
        """Write 32-bit value to two registers."""
        low = value & 0xFFFF
        high = (value >> 16) & 0xFFFF
        return self._modbus.write_registers(address, [low, high])
    
    def save_to_eeprom(self) -> bool:
        """
        Save parameters to EEPROM.
        
        Returns
        -------
        bool
            True if successful
        """
        logger.info("Saving parameters to EEPROM")
        # TODO: Implement EEPROM save command
        # This typically involves writing to a specific register
        # or sending a special command
        self._modified.clear()
        return True
    
    def restore_defaults(self) -> bool:
        """
        Restore factory default parameters.
        
        Returns
        -------
        bool
            True if successful
        """
        logger.warning("Restoring factory defaults")
        # TODO: Implement factory reset command
        self._cache.clear()
        self._modified.clear()
        return True
    
    def export_to_file(self, filename: str) -> bool:
        """
        Export parameters to JSON file.
        
        Parameters
        ----------
        filename : str
            Output filename
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            # Read all parameters
            params = {}
            for name, address in PARAMETER_ADDRESS.items():
                value = self.read(name)
                if value is not None:
                    params[name] = value
            
            # Save to file
            path = Path(filename)
            with open(path, 'w') as f:
                json.dump(params, f, indent=2)
            
            logger.info(f"Parameters exported to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export parameters: {e}")
            return False
    
    def import_from_file(self, filename: str) -> bool:
        """
        Import parameters from JSON file.
        
        Parameters
        ----------
        filename : str
            Input filename
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            path = Path(filename)
            with open(path, 'r') as f:
                params = json.load(f)
            
            # Write parameters
            for name, value in params.items():
                if name in PARAMETER_ADDRESS:
                    self.write(name, value)
                else:
                    logger.warning(f"Unknown parameter in file: {name}")
            
            logger.info(f"Parameters imported from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import parameters: {e}")
            return False
    
    def get_modified(self) -> set:
        """
        Get set of modified parameter names.
        
        Returns
        -------
        set
            Modified parameter names
        """
        return self._modified.copy()
    
    def clear_cache(self):
        """Clear parameter cache."""
        self._cache.clear()