import time
import random
import sys

# Import Adafruit libraries with error handling
try:
    import board
    import busio
    from adafruit_motorkit import MotorKit
    adafruit_imports_successful = True
except ImportError as e:
    print(f"Warning: Could not import Adafruit libraries: {e}")
    print("Real motor control will not be available.")
    adafruit_imports_successful = False

class RealMotorController:
    """Real motor controller that controls physical motors via I2C"""
    
    def __init__(self):
        """Initialize the motor controller with real hardware"""
        self.active_motors = {}  # Dictionary of active motors and their end times
        self.motor_queue = []  # Queue of (motor_id, activation_time) tuples for precise timing
        
        # Check if imports were successful
        if not adafruit_imports_successful:
            print("Adafruit libraries not available. Real motor control disabled.")
            self.hardware_available = False
            return
        
        # Try to initialize the motor hardware
        try:
            print("Initializing real motor controller...")
            
            # Initialize motor kits (8 boards with 4 motors each = 32 motors)
            self.kit = [MotorKit(address=96 + i) for i in range(8)]
            
            # Create a flat list of all motors
            self.motors = [motor for k in self.kit for motor in [k.motor1, k.motor2, k.motor3, k.motor4]]
            
            print(f"Successfully initialized {len(self.motors)} motors")
            self.hardware_available = True
            
            # Turn off all motors at startup
            self._deactivate_all_motors()
            
        except Exception as e:
            print(f"Error initializing motor hardware: {e}")
            print("Falling back to dummy motor controller")
            self.hardware_available = False
        
        # Motor mapping - map characters to motor IDs
        self.motor_map = {}
        for i, char in enumerate("abcdefghijklmnopqrstuvwxyz0123456789"):
            motor_id = i % 32  # Map to 32 motors
            self.motor_map[char] = motor_id
    
    def activate_for_char(self, char, char_time):
        """Activate the appropriate motor for a character at the exact time it appears"""
        # Get the motor ID for this character
        motor_id = self._get_motor_for_char(char)
        if motor_id is None:
            return
        
        # Queue the motor activation with precise timing
        self.motor_queue.append((motor_id, char_time))
        
        # Sort queue by activation time to ensure proper order
        self.motor_queue.sort(key=lambda x: x[1])
    
    def activate_for_chars(self, chars_with_times):
        """Queue motor activations for multiple characters with their exact times"""
        if not chars_with_times:
            return
            
        # Add all motors to the queue with their precise timing
        for char, char_time in chars_with_times:
            motor_id = self._get_motor_for_char(char)
            if motor_id is not None:
                self.motor_queue.append((motor_id, char_time))
        
        # Sort queue by activation time
        self.motor_queue.sort(key=lambda x: x[1])
    
    def _get_motor_for_char(self, char):
        """Get the motor ID for a character"""
        char = char.lower()
        return self.motor_map.get(char)
    
    def _activate_motor(self, motor_id):
        """Activate a real motor"""
        if not self.hardware_available or motor_id >= len(self.motors):
            return
        
        try:
            # Set motor to full throttle (1.0)
            self.motors[motor_id].throttle = 1.0
            
            # Set a random duration between 0.1 and 0.3 seconds
            duration = random.uniform(0.1, 0.3)
            end_time = time.time() + duration
            self.active_motors[motor_id] = end_time
            
            # print(f"Motor {motor_id} activated for {duration:.2f} seconds")
        except Exception as e:
            print(f"Error activating motor {motor_id}: {e}")
    
    def _deactivate_motor(self, motor_id):
        """Deactivate a real motor"""
        if not self.hardware_available or motor_id >= len(self.motors):
            return
            
        try:
            # Set motor to stop (0.0)
            self.motors[motor_id].throttle = 0.0
            # print(f"Motor {motor_id} deactivated")
        except Exception as e:
            print(f"Error deactivating motor {motor_id}: {e}")
    
    def _deactivate_all_motors(self):
        """Deactivate all motors"""
        if not self.hardware_available:
            return
            
        try:
            for i in range(len(self.motors)):
                self.motors[i].throttle = 0.0
            print("All motors deactivated")
        except Exception as e:
            print(f"Error deactivating all motors: {e}")
    
    def update(self, current_time=None):
        """Update motor states with precise timing"""
        if current_time is None:
            current_time = time.time()
        
        # Process the motor queue based on the current playback time
        motors_to_activate = []
        remaining_queue = []
        
        for motor_id, activation_time in self.motor_queue:
            if current_time >= activation_time:
                motors_to_activate.append(motor_id)
            else:
                remaining_queue.append((motor_id, activation_time))
        
        # Update the queue
        self.motor_queue = remaining_queue
        
        # Activate motors that are due
        for motor_id in motors_to_activate:
            self._activate_motor(motor_id)
        
        # Check for motors that need to be deactivated
        motors_to_deactivate = []
        for motor_id, end_time in self.active_motors.items():
            if current_time >= end_time:
                motors_to_deactivate.append(motor_id)
        
        # Deactivate motors
        for motor_id in motors_to_deactivate:
            self._deactivate_motor(motor_id)
            del self.active_motors[motor_id]
    
    def cleanup(self):
        """Clean up resources and ensure all motors are off"""
        self._deactivate_all_motors() 