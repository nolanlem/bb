#!/usr/bin/env python3
import os
import sys
import argparse
import pygame
import numpy as np
from pygame.locals import *
import time
import json

from audio import AudioProcessor
from visualizer import Visualizer
from text_display import TextDisplay
from motor_controller import DummyMotorController
try:
    from real_motor_controller import RealMotorController
    real_motor_available = True
except ImportError:
    real_motor_available = False

# Constants
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
DEFAULT_FPS = 30

def parse_args():
    parser = argparse.ArgumentParser(description='Text display with motor control')
    parser.add_argument('--words', required=True, help='JSON file with word timecodes')
    parser.add_argument('--fps', type=int, default=30, help='Target frames per second')
    parser.add_argument('--motors', type=str, choices=['true', 'false'], default='false', 
                        help='Enable real motor control (true) or use dummy motors (false)')
    parser.add_argument('--duration', type=float, default=60.0, help='Duration in seconds')
    parser.add_argument('--fullscreen', type=str, choices=['true', 'false'], default='true', 
                        help='Run in fullscreen mode (true) or windowed mode (false)')
    parser.add_argument('--print-json', action='store_true', help='Print the JSON structure and exit')
    parser.add_argument('--window-size', type=str, default='1280x720', 
                        help='Window size in format WIDTHxHEIGHT (only used in windowed mode)')
    parser.add_argument('--optimize', action='store_true', help='Enable additional optimizations for Raspberry Pi')
    return parser.parse_args()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Text display with motor control')
    parser.add_argument('--words', required=True, help='JSON file with word timecodes')
    parser.add_argument('--fps', type=int, default=15, help='Target frames per second')
    parser.add_argument('--motors', type=str, choices=['true', 'false'], default='false', 
                        help='Enable real motor control (true) or use dummy motors (false)')
    parser.add_argument('--fullscreen', type=str, choices=['true', 'false'], default='true', 
                        help='Run in fullscreen mode (true) or windowed mode (false)')
    parser.add_argument('--print-json', action='store_true', help='Print the JSON structure and exit')
    parser.add_argument('--window-size', type=str, default='800x480', 
                        help='Window size in format WIDTHxHEIGHT (only used in windowed mode)')
    parser.add_argument('--optimize', action='store_true', help='Enable additional optimizations for Raspberry Pi')
    args = parser.parse_args()
    
    # Set environment variables for better performance on Raspberry Pi
    if args.optimize:
        os.environ['SDL_VIDEODRIVER'] = 'fbcon'
        os.environ['SDL_FBDEV'] = '/dev/fb0'
    
    # Initialize pygame with reduced features for better performance
    pygame.init()
    if args.optimize:
        pygame.display.set_mode((0, 0), pygame.NOFRAME)
    
    # Set up display based on fullscreen flag
    fullscreen = args.fullscreen.lower() == 'true'
    
    if fullscreen:
        print("Running in fullscreen mode")
        if args.optimize:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        # Parse window size
        try:
            width, height = map(int, args.window_size.split('x'))
        except:
            print(f"Invalid window size format: {args.window_size}. Using default 800x480.")
            width, height = 800, 480
        
        print(f"Running in windowed mode ({width}x{height})")
        if args.optimize:
            screen = pygame.display.set_mode((width, height), pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            screen = pygame.display.set_mode((width, height))
    
    pygame.display.set_caption('Text Display')
    
    # Initialize motor controller based on argument
    use_real_motors = args.motors.lower() == 'true'
    
    if use_real_motors:
        if real_motor_available:
            motor_controller = RealMotorController()
            if not motor_controller.hardware_available:
                print("Real motor hardware not detected, falling back to dummy controller")
                motor_controller = DummyMotorController()
        else:
            print("Real motor controller module not available, falling back to dummy controller")
            motor_controller = DummyMotorController()
    else:
        print("Using dummy motor controller")
        motor_controller = DummyMotorController()
    
    # Create text display with the appropriate motor controller
    text_display = TextDisplay(screen, motor_controller)
    
    # Load word data
    if not text_display.load_word_data(args.words):
        print(f"Failed to load word data from {args.words}")
        if hasattr(motor_controller, 'cleanup'):
            motor_controller.cleanup()
        pygame.quit()
        sys.exit(1)
    
    # Print JSON structure if requested and exit
    if args.print_json:
        import json
        print("JSON structure:")
        print(json.dumps(text_display.word_data, indent=2))
        if hasattr(motor_controller, 'cleanup'):
            motor_controller.cleanup()
        pygame.quit()
        sys.exit(0)
    
    # For FPS calculation and frame limiting
    frame_count = 0
    start_time = time.time()
    last_fps_print = start_time
    last_frame_time = start_time
    target_frame_time = 1.0 / args.fps
    
    # Main loop
    running = True
    playback_start_time = time.time()
    
    # Calculate end time based on the last character's timing
    if text_display.all_chars:
        last_char_time = text_display.all_chars[-1][1]
        end_time = last_char_time + 5.0
        print(f"Will run until time {end_time:.1f} seconds")
    else:
        end_time = 60.0
        print("No characters found in JSON file. Will run for 60 seconds.")
    
    # Reduce CPU usage by limiting event processing frequency
    event_check_interval = 0.1
    last_event_check = 0
    
    try:
        while running:
            current_time = time.time()
            
            # Process events less frequently to reduce CPU usage
            if current_time - last_event_check >= event_check_interval:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                last_event_check = current_time
            
            # Calculate current playback time
            current_playback_time = current_time - playback_start_time
            
            # Check if we've reached the end of the playback
            if current_playback_time >= end_time:
                print("Reached end of playback")
                running = False
            
            # Check if we've displayed all characters
            if text_display.all_chars and text_display.current_char_index >= len(text_display.all_chars):
                if current_playback_time >= text_display.all_chars[-1][1] + 5.0:
                    print("All text displayed, exiting")
                    running = False
            
            # Limit frame rate
            elapsed = current_time - last_frame_time
            if elapsed < target_frame_time:
                remaining = target_frame_time - elapsed
                if remaining > 0.001:
                    time.sleep(remaining)
            
            last_frame_time = time.time()
            frame_count += 1
            
            # Update text display
            if text_display.update(current_playback_time):
                # Draw text display
                text_display.draw()
                pygame.display.flip()
            
            # Calculate and print FPS less frequently
            if time.time() - last_fps_print >= 5.0:
                fps = frame_count / (time.time() - last_fps_print)
                print(f"FPS: {fps:.1f}")
                frame_count = 0
                last_fps_print = time.time()
    
    finally:
        # Ensure motors are turned off when exiting
        if hasattr(motor_controller, 'cleanup'):
            motor_controller.cleanup()
        
        # Clean up
        pygame.quit()
        sys.exit(0)

if __name__ == "__main__":
    main() 