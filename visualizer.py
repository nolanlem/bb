import pygame
import numpy as np
import random
import math
from pygame.locals import *
import os
import json
from motor_controller import DummyMotorController
import time

# Add at the beginning of your main.py
os.environ['SDL_VIDEO_CENTERED'] = '1'

# If you're having issues with PyAudio on macOS, you can try:
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

class Visualizer:
    def __init__(self, screen, style, width, height):
        self.screen = screen
        self.width = width
        self.height = height
        self.style = style
        self.styles = ['crt', 'neon', 'mono', 'oscilloscope', 'vaporwave']
        
        # Initialize colors
        self.randomize_colors()
        
        # CRT effect parameters
        self.scan_line_interval = 2  # More scan lines for more retro feel
        self.scan_line_alpha = 80    # More visible scan lines
        self.crt_curve = 0.05        # More pronounced curve
        self.glitch_intensity = 0.2  # VHS glitch effect intensity
        
        # Create surfaces for effects
        self.main_surface = pygame.Surface((width, height))
        self.scan_lines = pygame.Surface((width, height), pygame.SRCALPHA)
        self.noise_texture = pygame.Surface((width, height), pygame.SRCALPHA)
        self._create_scan_lines()
        self._create_noise_texture()
        
        # Font for text
        try:
            self.font = pygame.font.Font(None, 20)  # Use a more pixelated font
        except:
            self.font = pygame.font.SysFont('monospace', 16)
        
        # History for oscilloscope
        self.history = []
        self.max_history = 100
        
        # Vaporwave grid
        self.grid_spacing = 20
        self.grid_horizon = height * 0.7
        
        # Animation timing
        self.time = 0
        self.last_glitch = 0
        self.glitch_duration = 0
        
        # Bar style
        self.bar_style = 'chunky'  # 'chunky', 'pixelated', 'glitchy'
        
        # Initialize visualization parameters
        self.bar_width = 30
        self.bar_spacing = 10
        self.max_bar_height = height * 0.8
        self.base_line = height * 0.9
        
        # For oscilloscope mode
        self.points_history = []
        self.max_history = 10
        
        # For CRT effect
        self.frame_count = 0
        
        # Create scan line overlay
        self.scan_lines = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, self.scan_line_interval):
            pygame.draw.line(self.scan_lines, (0, 0, 0, self.scan_line_alpha), 
                            (0, y), (width, y), 1)
        
        # Adjust for Retina display if needed
        self.retina_scale = 1
        if hasattr(pygame.display, 'get_window_size'):
            window_size = pygame.display.get_window_size()
            if window_size[0] > width:
                self.retina_scale = window_size[0] / width
        
        # Adjust scan line parameters for Retina displays
        self.scan_line_interval = max(2, int(4 * self.retina_scale))
        
        # Typewriter effect variables
        self.word_data = None
        self.current_text = ""
        self.target_text = ""
        self.display_text = ""
        self.last_char_time = 0
        self.char_delay = 0.03
        self.word_history = []
        self.max_word_history = 3
        self.typewriter_position = 0
        self.current_segment_index = -1
        self.time_offset = 0.0
        
        # Text box management
        self.max_lines_in_box = 5
        self.current_lines_count = 0
        self.should_clear_box = False
        
        # Text colors
        self.text_color = (220, 220, 220)  # Light gray for most text
        self.highlight_color = (255, 165, 0)  # Orange for the newest character
        self.history_color = (150, 150, 150)  # Dimmer gray for history
        
        # Character tracking
        self.last_char_added = ""
        self.char_highlight_duration = 0.2  # How long to highlight the newest character
        
        # Font for typewriter text - large but not too large
        try:
            self.text_font = pygame.font.Font(None, 36)  # Adjusted size
        except:
            self.text_font = pygame.font.SysFont('monospace', 32)
        
        # Text display area
        self.text_area = pygame.Rect(
            width * 0.1,  # 10% margin from left
            height * 0.7,  # 70% down from top
            width * 0.8,  # 80% of screen width
            height * 0.25  # 25% of screen height
        )
        
        # Initialize motor controller
        try:
            self.motor_controller = DummyMotorController()
        except Exception as e:
            print(f"Error initializing motor controller: {e}")
            self.motor_controller = None
        
        # More aggressive performance settings
        self.frame_rate = 20  # Lower frame rate
        self.last_frame_time = 0
        self.frame_interval = 1.0 / self.frame_rate
        
        # Reduce visualization complexity
        self.num_bars = 32  # Fewer bars
        self.bar_width = width // self.num_bars
        
        # Skip frames for heavy operations
        self.heavy_ops_frame_skip = 3  # Only do heavy operations every 3 frames
        self.frame_count = 0
        
        # Reduce surface creation
        self.background = pygame.Surface((width, height))
        self._setup_background()  # Pre-render the background
        
        # Pre-render common text elements
        self.text_cache = {}
    
    def _create_scan_lines(self):
        """Create CRT scan lines effect"""
        for y in range(0, self.height, self.scan_line_interval):
            alpha = self.scan_line_alpha + random.randint(-20, 20)  # Vary the intensity
            alpha = max(0, min(255, alpha))
            pygame.draw.line(self.scan_lines, (0, 0, 0, alpha), 
                            (0, y), (self.width, y), 1)
    
    def _create_noise_texture(self):
        """Create a static noise texture for grain effect"""
        for y in range(0, self.height, 2):
            for x in range(0, self.width, 2):
                # Create random static noise
                alpha = random.randint(0, 40)  # Subtle noise
                self.noise_texture.set_at((x, y), (255, 255, 255, alpha))
    
    def randomize_colors(self):
        """Randomize the color palette with vaporwave/lo-fi theme"""
        # Vaporwave palette options
        palettes = [
            # Classic vaporwave
            [(255, 165, 0), (255, 105, 180), (20, 10, 0)],
            # Outrun sunset
            [(255, 165, 0), (138, 43, 226), (20, 10, 30)],
            # Miami vice
            [(255, 165, 0), (0, 255, 255), (20, 0, 20)],
            # Retro orange
            [(255, 165, 0), (200, 120, 0), (20, 10, 0)]
        ]
        
        # Choose a random palette
        palette = random.choice(palettes)
        
        if self.style == 'crt':
            self.primary_color = palette[0]
            self.secondary_color = palette[1]
            self.bg_color = palette[2]
        elif self.style == 'neon':
            self.primary_color = palette[0]
            self.secondary_color = palette[1]
            self.bg_color = (10, 10, 20)
        elif self.style == 'mono':
            self.primary_color = (255, 165, 0)  # Orange
            self.secondary_color = (200, 120, 0)  # Darker orange
            self.bg_color = (20, 10, 0)
        elif self.style == 'oscilloscope':
            self.primary_color = (255, 165, 0)  # Orange
            self.secondary_color = (200, 120, 0)  # Darker orange
            self.bg_color = (0, 0, 0)
        elif self.style == 'vaporwave':
            self.primary_color = palette[0]
            self.secondary_color = palette[1]
            self.bg_color = (20, 0, 30)  # Deep purple/blue background
    
    def cycle_style(self):
        """Cycle through available visualization styles"""
        current_index = self.styles.index(self.style)
        next_index = (current_index + 1) % len(self.styles)
        self.style = self.styles[next_index]
        self.randomize_colors()
        
        # Also cycle through bar styles
        bar_styles = ['chunky', 'pixelated', 'glitchy']
        current_bar_index = bar_styles.index(self.bar_style)
        next_bar_index = (current_bar_index + 1) % len(bar_styles)
        self.bar_style = bar_styles[next_bar_index]
    
    def _setup_background(self):
        """Pre-render the background to avoid recreating it every frame"""
        if self.style == 'vaporwave':
            # Simplified vaporwave background
            self.background.fill((25, 25, 40))
            
            # Draw just a few grid lines instead of many
            for i in range(0, self.width, 40):
                pygame.draw.line(self.background, (60, 20, 120), (i, 0), (i, self.height), 1)
            for i in range(0, self.height, 40):
                pygame.draw.line(self.background, (60, 20, 120), (0, i), (self.width, i), 1)
        
        elif self.style == 'minimal':
            self.background.fill((10, 10, 10))
        
        else:  # Default style
            self.background.fill((0, 0, 0))
    
    def update(self, freq_data, current_time):
        """Update the visualization with new frequency data"""
        # Throttle updates to the target frame rate
        current_frame_time = time.time()
        if current_frame_time - self.last_frame_time < self.frame_interval:
            return False  # No update needed
        
        self.last_frame_time = current_frame_time
        self.time = current_time
        self.frame_count += 1
        
        # Only do heavy operations every few frames
        do_heavy_ops = (self.frame_count % self.heavy_ops_frame_skip == 0)
        
        # Update typewriter effect
        self.update_typewriter(current_time)
        
        # Store frequency data for visualization
        if freq_data is not None:
            # Downsample frequency data to match number of bars
            if len(freq_data) > self.num_bars:
                # Simple downsampling - take every nth value
                step = len(freq_data) // self.num_bars
                self.freq_data = [freq_data[i * step] for i in range(self.num_bars)]
            else:
                self.freq_data = freq_data
        
        return True  # Update was performed
    
    def draw(self):
        """Draw the visualization to the screen"""
        # Start with the pre-rendered background
        self.main_surface.blit(self.background, (0, 0))
        
        # Draw frequency bars (simplified)
        if hasattr(self, 'freq_data') and len(self.freq_data) > 0:
            for i, value in enumerate(self.freq_data):
                # Scale value to bar height
                bar_height = int(value * self.height * 0.5)
                
                # Draw a simple rectangle instead of a fancy bar
                bar_rect = pygame.Rect(
                    i * self.bar_width, 
                    self.height - bar_height,
                    self.bar_width - 2, 
                    bar_height
                )
                pygame.draw.rect(self.main_surface, self.primary_color, bar_rect)
        
        # Draw typewriter text
        self._draw_typewriter_text()
        
        # Blit to screen
        self.screen.blit(self.main_surface, (0, 0))
    
    def _draw_typewriter_text(self):
        """Draw the typewriter text effect - with performance optimizations"""
        if not self.word_data:
            return
        
        # Create a semi-transparent background for text (only once)
        if not hasattr(self, 'text_bg'):
            self.text_bg = pygame.Surface((self.text_area.width, self.text_area.height), pygame.SRCALPHA)
            self.text_bg.fill((0, 0, 0, 160))
        
        # Blit the background
        self.main_surface.blit(self.text_bg, self.text_area)
        
        # Draw border around text area
        pygame.draw.rect(self.main_surface, self.secondary_color, self.text_area, 1)
        
        # Calculate line height based on font
        line_height = self.text_font.get_height() + 5
        
        # Draw history text (previous lines)
        y_offset = 10  # Initial padding
        
        for i, history_text in enumerate(self.word_history):
            # Use cached text surfaces when possible
            cache_key = f"history_{history_text}"
            if cache_key not in self.text_cache:
                # Wrap text if needed
                wrapped_lines = self._wrap_text(history_text, self.text_area.width - 20)
                self.text_cache[cache_key] = []
                
                for line in wrapped_lines:
                    # Render with a dimmer color for history
                    history_surf = self.text_font.render(line, True, self.history_color)
                    self.text_cache[cache_key].append(history_surf)
            
            # Draw from cache
            for line_surf in self.text_cache[cache_key]:
                history_x = self.text_area.x + 10
                history_y = self.text_area.y + y_offset
                self.main_surface.blit(line_surf, (history_x, history_y))
                y_offset += line_height
        
        # Draw current text with typewriter effect
        if self.display_text:
            # Wrap current text
            wrapped_lines = self._wrap_text(self.display_text, self.text_area.width - 20)
            
            # Check if adding these lines would exceed our limit
            if y_offset + (len(wrapped_lines) * line_height) > self.text_area.height - 10:
                # We would overflow, so clear the box
                self.word_history = []
                y_offset = 10  # Reset to top
                self.current_lines_count = 0
                self.text_cache = {}  # Clear the cache
                
                # Show clearing animation next frame
                self.should_clear_box = True
            
            # Render each line
            for i, line in enumerate(wrapped_lines):
                # For the last line, we might need to highlight the newest character
                if i == len(wrapped_lines) - 1 and self.last_char_added and self.time - self.last_char_time < self.char_highlight_duration:
                    # This line contains the newest character
                    # Find the position of the last character
                    last_char_pos = line.rfind(self.last_char_added)
                    
                    if last_char_pos >= 0:
                        # Split the line into parts
                        before_char = line[:last_char_pos]
                        the_char = line[last_char_pos]
                        after_char = line[last_char_pos + 1:]
                        
                        # Cache key for this specific state
                        cache_key = f"current_{before_char}_{the_char}_{after_char}"
                        
                        if cache_key not in self.text_cache:
                            # Render each part
                            before_surf = self.text_font.render(before_char, True, self.text_color)
                            char_surf = self.text_font.render(the_char, True, self.highlight_color)
                            after_surf = self.text_font.render(after_char, True, self.text_color)
                            
                            # Create a combined surface
                            combined_width = before_surf.get_width() + char_surf.get_width() + after_surf.get_width()
                            combined_height = max(before_surf.get_height(), char_surf.get_height(), after_surf.get_height())
                            combined_surf = pygame.Surface((combined_width, combined_height), pygame.SRCALPHA)
                            
                            # Blit each part to the combined surface
                            combined_surf.blit(before_surf, (0, 0))
                            combined_surf.blit(char_surf, (before_surf.get_width(), 0))
                            combined_surf.blit(after_surf, (before_surf.get_width() + char_surf.get_width(), 0))
                            
                            # Cache the combined surface
                            self.text_cache[cache_key] = combined_surf
                        
                        # Blit the cached surface
                        text_x = self.text_area.x + 10
                        text_y = self.text_area.y + y_offset
                        self.main_surface.blit(self.text_cache[cache_key], (text_x, text_y))
                    else:
                        # Fallback if character not found
                        cache_key = f"line_{line}"
                        if cache_key not in self.text_cache:
                            self.text_cache[cache_key] = self.text_font.render(line, True, self.text_color)
                        self.main_surface.blit(self.text_cache[cache_key], (self.text_area.x + 10, self.text_area.y + y_offset))
                else:
                    # Regular line without highlighting
                    cache_key = f"line_{line}"
                    if cache_key not in self.text_cache:
                        self.text_cache[cache_key] = self.text_font.render(line, True, self.text_color)
                    self.main_surface.blit(self.text_cache[cache_key], (self.text_area.x + 10, self.text_area.y + y_offset))
                
                y_offset += line_height
            
            # Add blinking cursor at the end
            if wrapped_lines:
                cursor_visible = int(self.time * 2) % 2 == 0  # Blink cursor
                if cursor_visible:
                    cursor_x = self.text_area.x + 10 + self.text_font.render(wrapped_lines[-1], True, (0,0,0)).get_width()
                    cursor_y = self.text_area.y + y_offset - line_height
                    
                    # Cache the cursor
                    if "cursor" not in self.text_cache:
                        self.text_cache["cursor"] = self.text_font.render("█", True, self.highlight_color)
                    
                    self.main_surface.blit(self.text_cache["cursor"], (cursor_x, cursor_y))
    
    def _wrap_text(self, text, max_width):
        """Wrap text to fit within a given width"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            # Test width with current word added
            test_line = ' '.join(current_line + [word])
            test_surf = self.text_font.render(test_line, True, (0, 0, 0))
            
            if test_surf.get_width() <= max_width:
                # Word fits, add it to the current line
                current_line.append(word)
            else:
                # Word doesn't fit, start a new line
                if current_line:  # Only add if we have words
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        # Add the last line if there's anything left
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def load_word_data(self, json_file):
        """Load word timing data from a JSON file"""
        try:
            with open(json_file, 'r') as f:
                self.word_data = json.load(f)
                print(f"Loaded word timing data with {len(self.word_data['segments'])} segments")
                
                # Pre-process segments for easier access
                self.segments = self.word_data['segments']
                for segment in self.segments:
                    # Sort words by start time
                    segment['words'] = sorted(segment['words'], key=lambda x: x['start'])
                
                # Sort segments by start time
                self.segments = sorted(self.segments, key=lambda x: x['start'])
                
                # Initialize with empty text
                self.current_text = ""
                self.target_text = ""
                self.display_text = ""
                
        except Exception as e:
            print(f"Error loading word data: {e}")
            self.word_data = None

    def update_typewriter(self, current_time):
        """Update the typewriter text based on current playback time"""
        if not self.word_data:
            return
        
        # Apply the time offset
        adjusted_time = current_time + self.time_offset
        
        # Find the current segment
        current_segment = None
        current_segment_index = -1
        
        for i, segment in enumerate(self.segments):
            if segment['start'] <= adjusted_time <= segment['end']:
                current_segment = segment
                current_segment_index = i
                break
            elif adjusted_time < segment['start']:
                # We haven't reached this segment yet
                break
        
        # If we've moved to a new segment, reset the text
        if current_segment_index != self.current_segment_index:
            if current_segment_index > self.current_segment_index:
                # Moving forward - add previous segment to history
                if self.current_segment_index >= 0 and self.segments[self.current_segment_index]['text'].strip():
                    # Check if we need to clear the box
                    wrapped_lines = self._wrap_text(self.segments[self.current_segment_index]['text'].strip(), 
                                                  self.text_area.width - 20)
                    
                    # If adding these lines would exceed our limit, clear the box
                    if self.current_lines_count + len(wrapped_lines) > self.max_lines_in_box:
                        self.word_history = []  # Clear history
                        self.current_lines_count = 0  # Reset counter
                        self.should_clear_box = True  # Set flag to show clearing animation
                    else:
                        # Add to history normally
                        self.word_history.append(self.segments[self.current_segment_index]['text'].strip())
                        self.current_lines_count += len(wrapped_lines)
            
            self.current_segment_index = current_segment_index
            self.typewriter_position = 0
            self.current_text = ""
            self.target_text = ""
            self.display_text = ""
            self.last_char_added = ""
            
            if current_segment:
                self.target_text = current_segment['text']
        
        # If we have a current segment, update the typewriter
        if current_segment:
            # We'll build the visible text character by character based on timing
            visible_text = ""
            
            # Process each word in the segment to determine character timings
            char_timings = []
            
            for word_data in current_segment['words']:
                word = word_data['word']
                word_start = word_data['start']
                word_end = word_data['end']
                
                # Calculate time for each character in the word
                if len(word) > 0:
                    char_duration = (word_end - word_start) / len(word)
                    
                    for i, char in enumerate(word):
                        # Calculate when this character should appear
                        char_time = word_start + (i * char_duration)
                        char_timings.append((char, char_time))
            
            # Sort characters by their appearance time
            char_timings.sort(key=lambda x: x[1])
            
            # Determine which characters should be visible now
            visible_chars = []
            for char, char_time in char_timings:
                if adjusted_time >= char_time:
                    visible_chars.append(char)
            
            # Build the visible text
            visible_text = ''.join(visible_chars)
            
            # Check if we've added new characters
            if len(visible_text) > len(self.current_text):
                # New character(s) added
                new_chars = visible_text[len(self.current_text):]
                
                # For each new character, trigger the motor
                for char in new_chars:
                    self.last_char_added = char
                    self.last_char_time = self.time
                    
                    # Activate motor for this character
                    if self.motor_controller:
                        self.motor_controller.activate_for_char(char)
            
            # Update the current text
            self.current_text = visible_text
            
            # Set display text directly to what should be visible
            self.display_text = self.current_text 