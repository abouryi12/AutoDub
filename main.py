#!/usr/bin/env python3
"""
YouTube Auto Dub - Day 02
Added basic configuration and utilities
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from core_utils import setup_directories, validate_url
except ImportError:
    print("Error: core_utils not found!")
    sys.exit(1)

def main():
    print("YouTube Auto Dub - Starting...")
    
    # Setup directories
    setup_directories()
    
    # TODO: Get YouTube URL from user
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Placeholder
    
    # Validate URL
    if validate_url(youtube_url):
        print(f"URL is valid: {youtube_url}")
    else:
        print("Invalid URL!")
        return
    
    # TODO: Implement YouTube video download
    # TODO: Implement audio processing
    # TODO: Implement text translation
    # TODO: Implement voice synthesis
    
    print("YouTube Auto Dub - Finished!")

if __name__ == "__main__":
    main()
