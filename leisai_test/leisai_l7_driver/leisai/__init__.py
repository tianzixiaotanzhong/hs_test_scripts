"""
Leisai L7 Series Servo Driver Library
=====================================

A Python library for controlling Leisai L7 series AC servo drivers.

Basic usage:
    >>> from leisai import L7Driver
    >>> with L7Driver('COM3') as driver:
    ...     driver.connect()
    ...     print(driver.get_position())

Full documentation is available at https://github.com/leisai/python-l7-driver
"""

__version__ = '1.0.0'
__author__ = 'Leisai Python Driver Team'
__all__ = [
    'L7Driver',
    'ControlMode', 
    'ServoStatus',
    'AlarmCode',
    'L7Exception',
    'CommunicationError',
    'ParameterError',
]

from .core.driver import L7Driver
from .core.constants import ControlMode, ServoStatus, AlarmCode
from .core.exceptions import L7Exception, CommunicationError, ParameterError

# Convenience function for quick connection
def connect(port, **kwargs):
    """
    Create and connect to an L7 servo driver.
    
    Parameters
    ----------
    port : str
        Serial port name (e.g., 'COM3' or '/dev/ttyUSB0')
    **kwargs
        Additional arguments passed to L7Driver
        
    Returns
    -------
    L7Driver
        Connected driver instance
        
    Examples
    --------
    >>> driver = leisai.connect('COM3', slave_id=1)
    >>> driver.get_position()
    0
    """
    driver = L7Driver(port, **kwargs)
    driver.connect()
    return driver