import time
import threading
import datetime
import heapq
import random

class DummyMotorController:
    """Motor controller that maintains precise timing while being efficient"""
    
    def __init__(self, batch_mode=False):
        """Initialize the motor controller"""
        self.active_motors = {}  # Dictionary of active motors and their end times
        self.batch_mode = batch_mode
        self.motor_queue = []  # Queue of (motor_id, activation_time) tuples for precise timing
        self.last_process_time = 0
        self.process_interval = 0.01  # Process queue every 10ms (still maintains 100Hz precision)
        
        # Motor mapping - in a real implementation, this would map characters to motor IDs
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
        """Activate a motor for a random duration"""
        # In a real implementation, this would send an I2C command
        duration = random.uniform(0.1, 0.3)  # Random duration between 0.1 and 0.3 seconds
        end_time = time.time() + duration
        self.active_motors[motor_id] = end_time
        # print(f"Motor {motor_id} activated for {duration:.2f} seconds")
    
    def update(self, current_time=None):
        """Update motor states with precise timing"""
        if current_time is None:
            current_time = time.time()
        
        # Process the motor queue based on the current playback time
        # This ensures motors activate at exactly the right moment
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
            # In a real implementation, this would send an I2C command
            del self.active_motors[motor_id]

# For real implementation with Adafruit MotorKit
class RealMotorController:
    """Real motor controller using Adafruit MotorKit"""
    
    def __init__(self):
        try:
            from adafruit_motorkit import MotorKit
            
            # Map of characters to motor indices (0-31)
            self.char_to_motor = {
                'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7,
                'i': 8, 'j': 9, 'k': 10, 'l': 11, 'm': 12, 'n': 13, 'o': 14, 'p': 15,
                'q': 16, 'r': 17, 's': 18, 't': 19, 'u': 20, 'v': 21, 'w': 22, 'x': 23,
                'y': 24, 'z': 25, '1': 26, '2': 27, '3': 28, '4': 29, '5': 30, '6': 31,
                '7': 0, '8': 1, '9': 2, '0': 3, ' ': None  # Space doesn't trigger a motor
            }
            
            # Track which motors are currently active
            self.active_motors = set()
            
            # Track when motors were last activated
            self.last_activation = {}
            
            # Start time for relative timestamps
            self.start_time = time.time()
            
            # Initialize motor boards
            self.boards = []
            for addr in range(96, 104):  # Addresses 96-103
                try:
                    kit = MotorKit(i2c_address=addr)
                    self.boards.append(kit)
                    print(f"[{self._get_timestamp()}] Initialized motor board at address {addr}")
                except Exception as e:
                    print(f"[{self._get_timestamp()}] Failed to initialize motor board at address {addr}: {e}")
            
            print(f"[{self._get_timestamp()}] Initialized {len(self.boards)} motor boards")
            
        except ImportError:
            print(f"[{self._get_timestamp()}] Error: adafruit_motorkit not available")
            raise
    
    def _get_timestamp(self):
        """Get a formatted timestamp for logging"""
        # Absolute timestamp (wall clock time)
        abs_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Relative timestamp (seconds since start)
        rel_time = time.time() - self.start_time
        
        return f"{abs_time} | +{rel_time:.3f}s"
    
    def activate_for_char(self, char):
        """Activate the motor for a specific character"""
        char = char.lower()  # Convert to lowercase
        
        if char not in self.char_to_motor or self.char_to_motor[char] is None:
            return  # No motor for this character
        
        motor_idx = self.char_to_motor[char]
        
        # Check if this motor was recently activated
        current_time = time.time()
        if motor_idx in self.last_activation:
            time_since_last = current_time - self.last_activation[motor_idx]
            if time_since_last < 0.2:
                # Don't retrigger if it was recently activated
                return
        
        # Update last activation time
        self.last_activation[motor_idx] = current_time
        
        # Calculate which board and which motor on that board
        board_idx = motor_idx // 4
        motor_on_board = motor_idx % 4
        
        if board_idx < len(self.boards):
            # Get the motor
            board = self.boards[board_idx]
            motor = getattr(board, f"motor{motor_on_board + 1}")
            
            # Activate the motor
            motor.throttle = 1.0
            print(f"[{self._get_timestamp()}] Activated motor {motor_idx} (Board {board_idx}, Motor {motor_on_board}) for character '{char}'")
            
            # Start a thread to turn off the motor after the duration
            threading.Thread(target=self._deactivate_after_delay, 
                            args=(board_idx, motor_on_board, 0.1)).start()
    
    def _deactivate_after_delay(self, board_idx, motor_on_board, delay):
        """Turn off a motor after a delay"""
        time.sleep(delay)
        
        if board_idx < len(self.boards):
            # Get the motor
            board = self.boards[board_idx]
            motor = getattr(board, f"motor{motor_on_board + 1}")
            
            # Deactivate the motor
            motor.throttle = 0.0
            print(f"[{self._get_timestamp()}] Deactivated motor (Board {board_idx}, Motor {motor_on_board})")

class OptimizedMotorController:
    """Motor controller optimized for Raspberry Pi"""
    
    def __init__(self):
        # Same character mapping as before
        self.char_to_motor = {
            'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7,
            'i': 8, 'j': 9, 'k': 10, 'l': 11, 'm': 12, 'n': 13, 'o': 14, 'p': 15,
            'q': 16, 'r': 17, 's': 18, 't': 19, 'u': 20, 'v': 21, 'w': 22, 'x': 23,
            'y': 24, 'z': 25, '1': 26, '2': 27, '3': 28, '4': 29, '5': 30, '6': 31,
            '7': 0, '8': 1, '9': 2, '0': 3, ' ': None
        }
        
        # Track when motors were last activated
        self.last_activation = {}
        
        # Start time for timestamps
        self.start_time = time.time()
        
        # Motor state tracking
        self.active_motors = set()
        
        # Event queue for motor deactivations (priority queue)
        self.deactivation_queue = []
        
        print(f"[{self._get_timestamp()}] OptimizedMotorController initialized")
    
    def _get_timestamp(self):
        """Get a formatted timestamp for logging"""
        abs_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        rel_time = time.time() - self.start_time
        return f"{abs_time} | +{rel_time:.3f}s"
    
    def activate_for_char(self, char):
        """Activate the motor for a specific character"""
        char = char.lower()
        
        if char not in self.char_to_motor or self.char_to_motor[char] is None:
            return
        
        motor_idx = self.char_to_motor[char]
        
        # Check if recently activated
        current_time = time.time()
        if motor_idx in self.last_activation:
            time_since_last = current_time - self.last_activation[motor_idx]
            if time_since_last < 0.2:
                return
        
        # Update last activation time
        self.last_activation[motor_idx] = current_time
        
        # Calculate board and motor
        board_idx = motor_idx // 4
        motor_on_board = motor_idx % 4
        
        # Log activation
        print(f"[{self._get_timestamp()}] MOTOR: Activating motor {motor_idx} (Board {board_idx}, Motor {motor_on_board}) for character '{char}'")
        
        # Add to active motors
        self.active_motors.add(motor_idx)
        
        # Schedule deactivation
        deactivation_time = current_time + 0.1  # 100ms activation
        heapq.heappush(self.deactivation_queue, (deactivation_time, motor_idx))
    
    def update(self):
        """Process any pending motor deactivations"""
        current_time = time.time()
        
        # Process all deactivations that are due
        while self.deactivation_queue and self.deactivation_queue[0][0] <= current_time:
            _, motor_idx = heapq.heappop(self.deactivation_queue)
            
            if motor_idx in self.active_motors:
                # Calculate board and motor
                board_idx = motor_idx // 4
                motor_on_board = motor_idx % 4
                
                # Log deactivation
                print(f"[{self._get_timestamp()}] MOTOR: Deactivating motor {motor_idx} (Board {board_idx}, Motor {motor_on_board})")
                
                # Remove from active motors
                self.active_motors.remove(motor_idx) 