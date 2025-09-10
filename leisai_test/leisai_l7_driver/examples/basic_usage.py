#!/usr/bin/env python
"""
Basic usage examples for Leisai L7 servo driver.

This script demonstrates common operations with the L7 servo driver.
"""

import logging
import time
from leisai import L7Driver, ControlMode, AlarmCode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_connection():
    """Example: Basic connection and status check."""
    print("\n" + "="*60)
    print("Example 1: Basic Connection")
    print("="*60)
    
    # Create driver instance
    driver = L7Driver(port='COM3', slave_id=1, baudrate=38400)
    
    try:
        # Connect to servo
        if driver.connect():
            print("✓ Connected successfully")
            
            # Check servo status
            if driver.is_ready():
                print("✓ Servo is ready")
            else:
                alarm = driver.get_alarm()
                print(f"✗ Servo not ready, alarm: {driver.get_alarm_description(alarm)}")
            
            # Read basic information
            position = driver.get_position()
            speed = driver.get_speed()
            torque = driver.get_torque()
            
            print(f"Position: {position} pulses")
            print(f"Speed: {speed} rpm")
            print(f"Torque: {torque}%")
            
    finally:
        driver.disconnect()
        print("Disconnected")


def example_position_control():
    """Example: Position control mode."""
    print("\n" + "="*60)
    print("Example 2: Position Control")
    print("="*60)
    
    with L7Driver('COM3') as driver:
        # Set position control mode
        driver.set_control_mode(ControlMode.POSITION)
        print("Control mode set to POSITION")
        
        # Configure parameters
        driver.write_parameter('gear_ratio_numerator', 10000)
        driver.write_parameter('gear_ratio_denominator', 131072)
        driver.write_parameter('position_loop_gain', 250)
        
        # Enable servo
        driver.servo_on()
        print("Servo enabled")
        
        # Monitor position
        for i in range(5):
            pos = driver.get_position()
            print(f"Position: {pos} pulses")
            time.sleep(0.5)
        
        # Disable servo
        driver.servo_off()
        print("Servo disabled")


def example_speed_control():
    """Example: Speed control mode."""
    print("\n" + "="*60)
    print("Example 3: Speed Control")
    print("="*60)
    
    with L7Driver('COM3') as driver:
        # Set speed control mode
        driver.set_control_mode(ControlMode.SPEED)
        print("Control mode set to SPEED")
        
        # Set acceleration
        driver.write_parameter('acceleration_time', 1000)
        driver.write_parameter('deceleration_time', 1000)
        
        # Enable servo
        driver.servo_on()
        
        # Set target speed
        driver.write_parameter('speed_command_1', 500)
        print("Target speed set to 500 rpm")
        
        # Monitor speed
        for i in range(10):
            speed = driver.get_speed()
            print(f"Current speed: {speed} rpm")
            time.sleep(0.5)
        
        # Stop
        driver.write_parameter('speed_command_1', 0)
        time.sleep(2)
        
        driver.servo_off()


def example_jog():
    """Example: JOG motion."""
    print("\n" + "="*60)
    print("Example 4: JOG Motion")
    print("="*60)
    
    with L7Driver('COM3') as driver:
        driver.servo_on()
        
        # JOG forward
        print("JOG forward at 200 rpm")
        driver.jog(speed=200, direction=True)
        time.sleep(2)
        
        # JOG reverse
        print("JOG reverse at 200 rpm")
        driver.jog(speed=200, direction=False)
        time.sleep(2)
        
        # Stop JOG
        driver.stop_jog()
        print("JOG stopped")
        
        driver.servo_off()


def example_homing():
    """Example: Homing sequence."""
    print("\n" + "="*60)
    print("Example 5: Homing")
    print("="*60)
    
    with L7Driver('COM3') as driver:
        driver.servo_on()
        
        # Start homing
        print("Starting homing sequence...")
        driver.home(mode=0, high_speed=500, low_speed=50)
        
        # Wait for homing to complete
        while not driver.is_homing_complete():
            print("Homing in progress...")
            time.sleep(0.5)
        
        print("Homing complete!")
        
        # Read home position
        position = driver.get_position()
        print(f"Home position: {position} pulses")
        
        driver.servo_off()


def example_monitoring():
    """Example: Status monitoring with callbacks."""
    print("\n" + "="*60)
    print("Example 6: Status Monitoring")
    print("="*60)
    
    def on_status_change(status):
        print(f"Status update: Position={status.get('position')}, "
              f"Speed={status.get('speed')}, Torque={status.get('torque')}")
    
    def on_alarm(alarm_code):
        if alarm_code != AlarmCode.NO_ALARM:
            print(f"⚠ Alarm detected: 0x{alarm_code:02X}")
        else:
            print("✓ Alarm cleared")
    
    with L7Driver('COM3') as driver:
        # Set callbacks
        driver.set_status_callback(on_status_change)
        driver.set_alarm_callback(on_alarm)
        
        # Monitor for 10 seconds
        print("Monitoring for 10 seconds...")
        time.sleep(10)
        
        print("Monitoring complete")


def example_parameter_management():
    """Example: Parameter management."""
    print("\n" + "="*60)
    print("Example 7: Parameter Management")
    print("="*60)
    
    with L7Driver('COM3') as driver:
        # Read parameters
        rigidity = driver.read_parameter('rigidity_level')
        inertia = driver.read_parameter('inertia_ratio')
        print(f"Current rigidity: {rigidity}")
        print(f"Current inertia ratio: {inertia}%")
        
        # Modify parameters
        driver.set_rigidity(20)
        driver.set_inertia_ratio(200)
        print("Parameters modified")
        
        # Export parameters
        driver.export_parameters('servo_params.json')
        print("Parameters exported to servo_params.json")
        
        # Save to EEPROM
        driver.save_parameters()
        print("Parameters saved to EEPROM")


def main():
    """Run all examples."""
    examples = [
        ("Connection", example_connection),
        ("Position Control", example_position_control),
        ("Speed Control", example_speed_control),
        ("JOG Motion", example_jog),
        ("Homing", example_homing),
        ("Monitoring", example_monitoring),
        ("Parameters", example_parameter_management),
    ]
    
    print("\n" + "="*70)
    print(" Leisai L7 Servo Driver - Usage Examples")
    print("="*70)
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n{i}. {name}")
    
    choice = input("\nSelect example (1-7) or 'a' for all: ").strip()
    
    if choice.lower() == 'a':
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"Error in {name}: {e}")
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(examples):
            name, func = examples[idx]
            try:
                func()
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Invalid choice")
    else:
        print("Invalid input")


if __name__ == '__main__':
    main()