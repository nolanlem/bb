import pygame
import json
import time
import numpy as np
import random
from motor_controller import DummyMotorController

class TextDisplay:
    """Optimized text display for Raspberry Pi"""
    
    def __init__(self, screen):
        """Initialize the text display"""
        # Store screen reference
        self.screen = screen
        self.width, self.height = screen.get_size()
        
        # Performance settings - reduced for Pi
        self.frame_rate = 15  # Reduced from 30 to 15 FPS
        self.last_frame_time = 0
        self.frame_interval = 1.0 / self.frame_rate
        
        # Colors
        self.bg_color = (0, 0, 0)  # Black background
        self.text_color = (220, 220, 220)  # Light gray for most text
        self.highlight_color = (255, 165, 0)  # Orange for the newest character
        
        # Font for typewriter text - use a simpler font with moderate size
        self.selected_font_name, self.text_font = self._get_efficient_font(96)  # Reduced from 144
        print(f"Using font: {self.selected_font_name}")
        
        # Text display area
        margin = self.width * 0.05
        self.text_area = pygame.Rect(
            margin,
            self.height * 0.05,
            self.width - (2 * margin),
            self.height * 0.9
        )
        
        # Text variables
        self.all_text = ""
        self.typed_text = ""
        self.last_char = ""
        self.last_char_time = 0
        self.highlight_duration = 0.2
        self.current_char_index = 0
        
        # Create background - use hardware acceleration if available
        try:
            self.background = pygame.Surface((self.width, self.height), pygame.HWSURFACE)
        except:
            self.background = pygame.Surface((self.width, self.height))
        self.background.fill(self.bg_color)
        
        # Text rendering cache to avoid re-rendering the same text
        self.text_cache = {}
        self.max_cache_size = 100  # Limit cache size to prevent memory issues
        
        # Initialize motor controller with batch mode
        try:
            self.motor_controller = DummyMotorController(batch_mode=True)
        except Exception as e:
            print(f"Error initializing motor controller: {e}")
            self.motor_controller = None
        
        # Data
        self.word_data = None
        self.all_chars = []
        
        # Performance monitoring
        self.render_time = 0
        self.update_time = 0
        self.frame_count = 0
    
    def _get_efficient_font(self, size):
        """Get a font that's efficient for rendering on Raspberry Pi"""
        # Reduce the size by 1/4 (to 75% of original size)
        reduced_size = int(size * 0.75)  # 75% of the original size
        
        # Simple fonts that render efficiently
        efficient_fonts = [
            'dejavu sans', 'liberation sans', 'freesans', 
            'droid sans', 'roboto', 'ubuntu', 'arial'
        ]
        
        # Try each font
        for font_name in efficient_fonts:
            try:
                font = pygame.font.SysFont(font_name, reduced_size)
                test_surface = font.render("Test", True, (255, 255, 255))
                if test_surface.get_width() > 10:
                    return font_name, font
            except:
                continue
        
        # Fallback to default
        try:
            return "Default", pygame.font.Font(None, reduced_size)
        except:
            return "Monospace", pygame.font.SysFont('monospace', reduced_size)
    
    def _get_cached_text_surface(self, text, color):
        """Get a cached text surface or render a new one"""
        cache_key = (text, color)
        if cache_key in self.text_cache:
            return self.text_cache[cache_key]
        
        # Render new surface
        surface = self.text_font.render(text, True, color)
        
        # Add to cache if not too large
        if len(self.text_cache) < self.max_cache_size:
            self.text_cache[cache_key] = surface
        
        return surface
    
    def load_word_data(self, json_file):
        """Load word timing data from a JSON file"""
        try:
            print(f"Loading word data from {json_file}")
            with open(json_file, 'r') as f:
                self.word_data = json.load(f)
            
            # Process the data into a flat list of characters with timings
            self.all_chars = []
            
            # Handle different JSON formats
            if isinstance(self.word_data, list):
                segments = self.word_data
            elif isinstance(self.word_data, dict) and 'segments' in self.word_data:
                segments = self.word_data['segments']
            else:
                print(f"Unknown JSON format: {type(self.word_data)}")
                return False
            
            # Process each segment
            for segment in segments:
                if 'words' in segment and isinstance(segment['words'], list):
                    for word_data in segment['words']:
                        word = word_data.get('word', '')
                        start_time = float(word_data.get('start', 0))
                        end_time = float(word_data.get('end', 0))
                        
                        # Calculate time for each character
                        if word and end_time > start_time:
                            char_duration = (end_time - start_time) / len(word)
                            for i, char in enumerate(word):
                                char_time = start_time + (i * char_duration)
                                self.all_chars.append((char, char_time))
                            
                            # Add space after word
                            self.all_chars.append((' ', end_time))
            
            # Sort by time
            self.all_chars.sort(key=lambda x: x[1])
            
            # Build the complete text
            self.all_text = ''.join(char for char, _ in self.all_chars)
            
            print(f"Loaded {len(self.all_chars)} characters")
            return True
        
        except Exception as e:
            print(f"Error loading word data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update(self, current_time):
        """Update the text display with precise motor timing"""
        # Throttle updates
        now = time.time()
        if now - self.last_frame_time < self.frame_interval:
            return False
        
        start_time = time.time()
        
        self.last_frame_time = now
        self.time = current_time
        
        # Track new characters with their exact timing
        new_chars_with_times = []
        
        # Determine which characters should be visible
        next_char_index = self.current_char_index
        for i in range(self.current_char_index, len(self.all_chars)):
            char, char_time = self.all_chars[i]
            if current_time >= char_time:
                next_char_index = i + 1
                
                # If this is a new character, process it
                if i >= self.current_char_index:
                    self.last_char = char
                    self.last_char_time = self.time
                    self.typed_text += char
                    new_chars_with_times.append((char, char_time))
            else:
                break
        
        # Update our position
        self.current_char_index = next_char_index
        
        # Activate motors with precise timing
        if self.motor_controller and new_chars_with_times:
            self.motor_controller.activate_for_chars(new_chars_with_times)
        
        # Update motor controller with current playback time for precise timing
        if self.motor_controller:
            self.motor_controller.update(current_time)
        
        self.update_time = time.time() - start_time
        return True
    
    def draw(self):
        """Draw the text display to the screen"""
        start_time = time.time()
        
        # Start with background
        self.screen.blit(self.background, (0, 0))
        
        # Draw text area background
        text_bg = pygame.Surface((self.text_area.width, self.text_area.height), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 160))
        self.screen.blit(text_bg, self.text_area)
        
        # Draw border
        pygame.draw.rect(self.screen, (100, 100, 100), self.text_area, 2)
        
        # Calculate line height
        line_height = self.text_font.get_height() + 10
        
        # Calculate max visible lines
        max_lines = int((self.text_area.height - 20) / line_height)
        
        # Wrap text - use cached version if available
        wrapped_lines = self._wrap_text(self.typed_text, self.text_area.width - 20)
        
        # Check if we need to clear
        if len(wrapped_lines) > max_lines:
            # Screen is full, need to clear
            self.typed_text = ""
            self.render_time = time.time() - start_time
            return
        
        # Draw text
        y_offset = 10
        
        for i, line in enumerate(wrapped_lines):
            # Check if this line has the newest character
            if i == len(wrapped_lines) - 1 and self.last_char and self.time - self.last_char_time < self.highlight_duration:
                # Find the last character
                last_char_pos = line.rfind(self.last_char)
                
                if last_char_pos >= 0:
                    # Split the line
                    before = line[:last_char_pos]
                    char = line[last_char_pos]
                    after = line[last_char_pos + 1:]
                    
                    # Render parts using cache
                    before_surf = self._get_cached_text_surface(before, self.text_color)
                    char_surf = self._get_cached_text_surface(char, self.highlight_color)
                    after_surf = self._get_cached_text_surface(after, self.text_color)
                    
                    # Draw parts
                    x = self.text_area.x + 10
                    y = self.text_area.y + y_offset
                    
                    self.screen.blit(before_surf, (x, y))
                    x += before_surf.get_width()
                    self.screen.blit(char_surf, (x, y))
                    x += char_surf.get_width()
                    self.screen.blit(after_surf, (x, y))
                else:
                    # Fallback
                    text_surf = self._get_cached_text_surface(line, self.text_color)
                    self.screen.blit(text_surf, (self.text_area.x + 10, self.text_area.y + y_offset))
            else:
                # Regular line
                text_surf = self._get_cached_text_surface(line, self.text_color)
                self.screen.blit(text_surf, (self.text_area.x + 10, self.text_area.y + y_offset))
            
            y_offset += line_height
        
        # Draw cursor - only every other frame to reduce rendering
        if wrapped_lines and self.frame_count % 2 == 0:
            cursor_visible = int(self.time * 2) % 2 == 0
            if cursor_visible:
                last_line = wrapped_lines[-1]
                cursor_x = self.text_area.x + 10 + self._get_cached_text_surface(last_line, (0,0,0)).get_width()
                cursor_y = self.text_area.y + y_offset - line_height
                cursor_surf = self._get_cached_text_surface("█", self.highlight_color)
                self.screen.blit(cursor_surf, (cursor_x, cursor_y))
        
        self.frame_count += 1
        self.render_time = time.time() - start_time
        
        # Print performance stats every 100 frames
        if self.frame_count % 100 == 0:
            print(f"Performance: Update: {self.update_time*1000:.1f}ms, Render: {self.render_time*1000:.1f}ms")
    
    def _wrap_text(self, text, max_width):
        """Wrap text to fit within a given width - with caching"""
        # Check if we already wrapped this text
        cache_key = (text, max_width)
        if hasattr(self, '_wrap_cache') and cache_key in self._wrap_cache:
            return self._wrap_cache[cache_key]
        
        # Initialize wrap cache if needed
        if not hasattr(self, '_wrap_cache'):
            self._wrap_cache = {}
            self._wrap_cache_size = 0
            self._max_wrap_cache = 20
        
        # Perform wrapping
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            # Test width with current word added
            test_line = ' '.join(current_line + [word])
            test_width = self._get_text_width(test_line)
            
            if test_width <= max_width:
                # Word fits, add it to the current line
                current_line.append(word)
            else:
                # Word doesn't fit, start a new line
                if current_line:  # Only add if we have words
                    lines.append(' '.join(current_line))
                
                # If the word itself is too long, we need to split it
                if self._get_text_width(word) > max_width:
                    # Split the word character by character
                    current_word = ""
                    for char in word:
                        test_word = current_word + char
                        if self._get_text_width(test_word) <= max_width:
                            current_word = test_word
                        else:
                            lines.append(current_word)
                            current_word = char
                    
                    if current_word:  # Add any remaining characters
                        current_line = [current_word]
                    else:
                        current_line = []
                else:
                    current_line = [word]
        
        # Add the last line if there's anything left
        if current_line:
            lines.append(' '.join(current_line))
        
        # Cache the result if cache isn't too large
        if self._wrap_cache_size < self._max_wrap_cache:
            self._wrap_cache[cache_key] = lines
            self._wrap_cache_size += 1
        
        return lines
    
    def _get_text_width(self, text):
        """Get the width of text - with caching"""
        if not hasattr(self, '_width_cache'):
            self._width_cache = {}
        
        if text in self._width_cache:
            return self._width_cache[text]
        
        # Calculate width
        width = self._get_cached_text_surface(text, self.text_color).get_width()
        
        # Cache result
        if len(self._width_cache) < 1000:  # Limit cache size
            self._width_cache[text] = width
            
        return width 