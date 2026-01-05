"""
Language Map Generator for YouTube Auto Dub.

This script fetches the latest available voices from Microsoft Edge TTS
and generates a `language_map.json` file compatible with the 
Multi-Speaker Diarization system.

It groups voices into 'male' and 'female' lists (pools) for every language,
enabling the engine to rotate voices for different speakers automatically.

Usage: python latest_langmap_generate.py
"""

import asyncio
import json
import edge_tts
from pathlib import Path
from typing import Dict, List, Any

# Define path relative to project root (assuming this script is in root or src)
# Adjust BASE_DIR if you move this script.
BASE_DIR = Path(__file__).resolve().parent
LANG_MAP_FILE = BASE_DIR / "language_map.json"

async def generate_lang_map() -> None:
    print("[*] Connecting to Microsoft Edge TTS API...")
    
    try:
        # Fetch all available voices
        voices = await edge_tts.list_voices()
    except Exception as e:
        print(f"[!] CRITICAL: Failed to fetch voices: {e}")
        return

    print(f"[*] Processing {len(voices)} raw voice entries...")
    
    # Structure: { "vi": { "name": "vi-VN", "voices": { "male": [], "female": [] } } }
    lang_map: Dict[str, Any] = {}
    
    for v in voices:
        # 1. FILTER: Strict quality control - Neural voices only
        if "Neural" not in v["ShortName"]:
            continue
            
        # 2. EXTRACT: Parse metadata
        short_name = v["ShortName"]     # e.g., "vi-VN-NamMinhNeural"
        locale = v["Locale"]            # e.g., "vi-VN"
        gender = v["Gender"].lower()    # "male" or "female"
        
        # ISO Language Code (e.g., 'vi' from 'vi-VN')
        lang_code = locale.split('-')[0]
        
        # 3. INITIALIZE: Create structure if language not seen before
        if lang_code not in lang_map:
            lang_map[lang_code] = {
                "name": locale,  # Store locale as a friendly name reference
                "voices": {
                    "male": [],
                    "female": []
                }
            }
        
        # 4. POPULATE: Add voice to the specific gender pool
        # This creates the "List" structure required by engines.py
        target_list = lang_map[lang_code]["voices"].get(gender)
        
        # Handle case where gender might be undefined or new
        if target_list is None:
            lang_map[lang_code]["voices"][gender] = []
            target_list = lang_map[lang_code]["voices"][gender]
            
        if short_name not in target_list:
            target_list.append(short_name)

    # 5. OPTIMIZE: Remove languages with empty voice lists (optional cleanup)
    final_map = {
        k: v for k, v in lang_map.items() 
        if v["voices"]["male"] or v["voices"]["female"]
    }

    # 6. SAVE: Write to JSON
    try:
        with open(LANG_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(final_map, f, ensure_ascii=False, indent=2)
            
        print(f"\n[+] SUCCESS! Generated configuration for {len(final_map)} languages.")
        print(f"    File saved to: {LANG_MAP_FILE}")
        
        # Preview a specific language (e.g., Vietnamese)
        if "vi" in final_map:
            print("\n[*] Preview (Vietnamese):")
            print(json.dumps(final_map["vi"], indent=2))
            
    except Exception as e:
        print(f"[!] ERROR: Failed to write JSON file: {e}")

if __name__ == "__main__":
    asyncio.run(generate_lang_map())