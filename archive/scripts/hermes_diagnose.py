#!/usr/bin/env python3
"""
Diagnose and fix the audio file issue for Hermes transcription
"""

import subprocess
import os
from pathlib import Path

def check_audio_file():
    """Check the downloaded audio file"""
    
    # Find the most recent hermes session
    desktop = Path.home() / "Desktop"
    sessions = sorted([d for d in desktop.glob("hermes_session_*") if d.is_dir()])
    
    if not sessions:
        print("❌ No hermes session folders found")
        return
    
    latest_session = sessions[-1]
    print(f"📁 Checking session: {latest_session.name}")
    
    # Find the audio file
    audio_files = list(latest_session.glob("*.m4a"))
    
    if not audio_files:
        print("❌ No .m4a file found in session folder")
        return
    
    audio_file = audio_files[0]
    print(f"\n📊 Audio file: {audio_file.name}")
    
    # Check file size
    size_bytes = audio_file.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"   Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
    
    if size_mb < 1:
        print("   ⚠️  File seems too small for a 9-minute recording")
        print("   💡 This might be a Google Drive HTML redirect page, not the actual audio")
    
    # Check file type using 'file' command
    print("\n🔍 Checking actual file type...")
    result = subprocess.run(['file', str(audio_file)], capture_output=True, text=True)
    print(f"   Type: {result.stdout.strip()}")
    
    # Check first few bytes
    print("\n📝 First 100 bytes of file:")
    with open(audio_file, 'rb') as f:
        first_bytes = f.read(100)
        # Check if it's HTML (Google Drive redirect)
        if first_bytes.startswith(b'<!DOCTYPE') or first_bytes.startswith(b'<html'):
            print("   ❌ This is an HTML file, not audio!")
            print("   💡 Google Drive download was redirected")
            print("\n🔧 SOLUTION: Download directly from Google Drive")
            print("   1. Open: https://drive.google.com/file/d/1R18WHCYcCgdHDyggJ0r2EC69FJ9Ww08z/view")
            print("   2. Click the download button")
            print(f"   3. Save to: {latest_session}")
            print("   4. Run the transcribe script again")
        else:
            # Show hex dump
            hex_dump = ' '.join([f'{b:02x}' for b in first_bytes[:20]])
            print(f"   Hex: {hex_dump}")
            
            # Check for M4A signature
            if first_bytes[4:8] == b'ftyp':
                print("   ✅ Valid M4A/MP4 container detected")
            else:
                print("   ⚠️  Doesn't look like a valid M4A file")
    
    return audio_file

def download_with_gdown():
    """Alternative download using different method"""
    print("\n🔄 Attempting alternative download method...")
    
    # Find latest session
    desktop = Path.home() / "Desktop"
    sessions = sorted([d for d in desktop.glob("hermes_session_*") if d.is_dir()])
    latest_session = sessions[-1] if sessions else None
    
    if not latest_session:
        latest_session = desktop / "hermes_session_fixed"
        latest_session.mkdir(exist_ok=True)
    
    output_file = latest_session / "2025-07-29--0901.m4a"
    
    # Try different download approach
    file_id = "1R18WHCYcCgdHDyggJ0r2EC69FJ9Ww08z"
    
    # Method 1: Direct download with confirmation bypass
    print("🌐 Method 1: Direct download with cookie...")
    url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
    
    result = subprocess.run([
        'curl', '-L', 
        '-o', str(output_file),
        '--progress-bar',
        '-H', 'User-Agent: Mozilla/5.0',
        url
    ], capture_output=True)
    
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"   Downloaded: {size_mb:.2f} MB")
        
        # Check if it's actually audio
        result = subprocess.run(['file', str(output_file)], capture_output=True, text=True)
        file_type = result.stdout.strip()
        
        if 'HTML' in file_type or size_mb < 1:
            print("   ❌ Still getting HTML redirect")
            print("\n🔧 Manual download required:")
            print("   1. Open: https://drive.google.com/file/d/1R18WHCYcCgdHDyggJ0r2EC69FJ9Ww08z/view")
            print("   2. Click the download icon")
            print(f"   3. Save to: {latest_session}")
            print("\n   Then run:")
            print(f"   python3 ~/Projects/demestihas-ai/hermes_transcribe_fixed.py '{output_file}'")
        else:
            print(f"   ✅ Got audio file: {file_type}")
            return output_file
    
    return None

if __name__ == "__main__":
    print("🔍 Hermes Audio File Diagnostic")
    print("=" * 50)
    
    # Check existing file
    audio_file = check_audio_file()
    
    if audio_file:
        # Check if it's valid audio
        with open(audio_file, 'rb') as f:
            header = f.read(100)
            if b'HTML' in header or b'<!DOCTYPE' in header:
                print("\n🔄 File is HTML, attempting re-download...")
                new_file = download_with_gdown()
                if new_file:
                    print(f"\n✅ Ready to transcribe: {new_file}")
    else:
        print("\n🔄 No audio file found, attempting download...")
        new_file = download_with_gdown()
