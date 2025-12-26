#!/usr/bin/env python3
"""
Fixed Hermes Transcribe - Works with local audio file
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import urllib.request
import json

def get_api_key():
    """Get API key from storage or environment"""
    # Try environment first
    api_key = os.environ.get('OPENAI_API_KEY', '')
    
    # Try saved file
    if not api_key:
        key_file = Path.home() / '.openai_key'
        if key_file.exists():
            with open(key_file, 'r') as f:
                api_key = f.read().strip()
                if '=' in api_key:
                    api_key = api_key.split('=')[1].strip()
    
    # Ask if still not found
    if not api_key:
        print("🔑 OpenAI API key required")
        api_key = input("Enter your API key: ").strip()
    
    return api_key

def transcribe_audio(audio_path, api_key):
    """Transcribe audio file with Whisper"""
    print(f"\n🎙️  Transcribing: {Path(audio_path).name}")
    print("   This may take 1-2 minutes...")
    
    # Check file exists and size
    if not os.path.exists(audio_path):
        print(f"❌ File not found: {audio_path}")
        return None
    
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"   File size: {file_size_mb:.2f} MB")
    
    if file_size_mb < 1:
        print("   ⚠️  File seems too small, might not be valid audio")
    
    url = "https://api.openai.com/v1/audio/transcriptions"
    
    # Read the file
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # Check if it's actually HTML
    if audio_data[:100].startswith(b'<!DOCTYPE') or audio_data[:100].startswith(b'<html'):
        print("❌ This is an HTML file, not audio!")
        print("Please download the actual audio file from Google Drive")
        return None
    
    # Create multipart form data
    boundary = '----WebKitFormBoundary' + os.urandom(16).hex()
    
    # Build form data
    filename = Path(audio_path).name
    
    parts = []
    
    # Add file part
    parts.append(f'--{boundary}'.encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
    parts.append(b'Content-Type: audio/m4a')
    parts.append(b'')
    parts.append(audio_data)
    
    # Add model
    parts.append(f'--{boundary}'.encode())
    parts.append(b'Content-Disposition: form-data; name="model"')
    parts.append(b'')
    parts.append(b'whisper-1')
    
    # End
    parts.append(f'--{boundary}--'.encode())
    parts.append(b'')
    
    body = b'\r\n'.join(parts)
    
    # Create request
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.data = body
    
    try:
        print("   Sending to OpenAI...")
        response = urllib.request.urlopen(req)
        result = response.read().decode('utf-8')
        print("✅ Transcription successful!")
        return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ API Error {e.code}: {error_body}")
        
        # Parse error
        try:
            error_data = json.loads(error_body)
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            print(f"   Details: {error_msg}")
        except:
            pass
        
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def format_transcript(transcript_text, output_dir):
    """Format transcript in Hermes style"""
    
    output = f"""# 🎧 Hermes Transcription Report

**Audio File**: 2025-07-29--0901.m4a  
**Date Recorded**: July 29, 2025 @ 9:01 AM  
**Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Word Count**: {len(transcript_text.split())} words

---

## 📝 Raw Transcript

{transcript_text}

---

## 🔍 Human Verification Checklist

### Speaker Identification
- [ ] Speaker 1: _________________
- [ ] Speaker 2: _________________
- [ ] Additional: _________________

### Meeting Type & Context
- [ ] Type: [Strategy / Operational / Check-in / Other]
- [ ] Main Topics: _________________
- [ ] Duration: ~9 minutes

### Action Items to Extract
- [ ] Task: _________________ | Owner: _____ | Due: _____
- [ ] Task: _________________ | Owner: _____ | Due: _____
- [ ] Task: _________________ | Owner: _____ | Due: _____
- [ ] Task: _________________ | Owner: _____ | Due: _____

### Key Decisions
- [ ] Decision: _________________
- [ ] Decision: _________________

### Follow-ups Required
- [ ] Follow-up: _________________
- [ ] Follow-up: _________________

---

## 🎯 Kairos Beta Upload Format

```markdown
CONTEXT: [Meeting type]
DATE: 2025-07-29
PARTICIPANTS: [Names]

TASKS:
1. [Task] - @[owner] - ![priority] - #[due_date]
2. [Task] - @[owner] - ![priority] - #[due_date]

DECISIONS:
- [Decision]

NEXT_STEPS:
- [Action]
```

---

*Transcribed by Hermes Audio Pipeline*
"""
    
    # Save files
    output_file = output_dir / "hermes_transcript.md"
    with open(output_file, 'w') as f:
        f.write(output)
    
    raw_file = output_dir / "raw_transcript.txt"
    with open(raw_file, 'w') as f:
        f.write(transcript_text)
    
    return output_file

def main():
    print("🎧 Hermes Transcribe - Fixed Version")
    print("=" * 50)
    
    # Get audio file path
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        # Try to find in most recent session
        desktop = Path.home() / "Desktop"
        sessions = sorted([d for d in desktop.glob("hermes_session_*") if d.is_dir()])
        
        if sessions:
            latest = sessions[-1]
            audio_files = list(latest.glob("*.m4a"))
            if audio_files:
                audio_path = str(audio_files[0])
                print(f"📂 Found audio in: {latest.name}")
            else:
                print("Enter path to audio file:")
                audio_path = input().strip().strip('"')
        else:
            print("Enter path to audio file:")
            audio_path = input().strip().strip('"')
    
    if not os.path.exists(audio_path):
        print(f"❌ File not found: {audio_path}")
        return
    
    # Create output directory
    output_dir = Path(audio_path).parent
    
    # Get API key
    api_key = get_api_key()
    
    # Transcribe
    transcript = transcribe_audio(audio_path, api_key)
    
    if transcript:
        # Format and save
        output_file = format_transcript(transcript, output_dir)
        print(f"\n✅ Complete!")
        print(f"📁 Transcript saved to: {output_file}")
        
        # Open folder
        import subprocess
        subprocess.run(['open', str(output_dir)])
        print("\n📂 Folder opened in Finder")
        print("Review the transcript and extract action items for Kairos")
    else:
        print("\n❌ Transcription failed")
        print("\nTroubleshooting:")
        print("1. Verify the audio file is valid (not HTML)")
        print("2. Check your API key has credits")
        print("3. Make sure the file is actually .m4a audio")

if __name__ == "__main__":
    main()
