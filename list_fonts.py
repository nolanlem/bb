import pygame
import sys
import unicodedata

def is_latin_font(font_name):
    """Check if a font is likely to support Latin/English characters"""
    try:
        # Create a font object
        font = pygame.font.SysFont(font_name, 24)
        
        # Test characters that should be present in Latin fonts
        test_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        
        # Check if the font can render these characters
        for char in test_chars:
            if not font.get_metrics(char):
                return False
        
        # Additional check: try to render some text
        text_surface = font.render(test_chars, True, (255, 255, 255))
        if text_surface.get_width() < 10:  # If width is too small, rendering likely failed
            return False
        
        return True
    except:
        return False

def list_available_fonts():
    """List all available fonts in pygame that support English/Latin characters"""
    pygame.init()
    
    # Get the list of all available system fonts
    all_fonts = pygame.font.get_fonts()
    
    print("Checking fonts for Latin character support...")
    
    # Filter for Latin fonts
    latin_fonts = []
    for font in all_fonts:
        # Skip fonts with non-Latin names (likely to be non-Latin fonts)
        if any(c for c in font if unicodedata.category(c).startswith('Lo')):
            continue
            
        # Skip fonts with these keywords that often indicate non-Latin fonts
        skip_keywords = ['arabic', 'hebrew', 'thai', 'cjk', 'chinese', 'japanese', 
                         'korean', 'hindi', 'bengali', 'tamil', 'telugu', 'kannada',
                         'malayalam', 'gujarati', 'punjabi', 'devanagari']
        
        if any(keyword in font.lower() for keyword in skip_keywords):
            continue
        
        # Check if the font supports Latin characters
        if is_latin_font(font):
            latin_fonts.append(font)
    
    print(f"\nFound {len(latin_fonts)} fonts that support English/Latin characters:")
    
    # Print them in a nice format, sorted alphabetically
    for i, font in enumerate(sorted(latin_fonts)):
        print(f"{i+1:3d}. {font}")
    
    # Test some common English fonts
    print("\nTesting some common English fonts:")
    common_fonts = [
        'arial', 'times', 'georgia', 'verdana', 'tahoma', 
        'trebuchet', 'courier', 'helvetica', 'calibri', 
        'garamond', 'palatino', 'bookman', 'avant garde', 'gill sans'
    ]
    
    for font_name in common_fonts:
        try:
            font = pygame.font.SysFont(font_name, 24)
            # Test rendering
            text_surface = font.render("The quick brown fox jumps over the lazy dog", True, (255, 255, 255))
            if text_surface.get_width() > 10:
                print(f"✓ {font_name} - Available and renders correctly")
            else:
                print(f"✗ {font_name} - Available but doesn't render correctly")
        except Exception as e:
            print(f"✗ {font_name} - Not available ({e})")
    
    pygame.quit()

if __name__ == "__main__":
    list_available_fonts() 