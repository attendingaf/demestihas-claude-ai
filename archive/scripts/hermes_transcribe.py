#!/usr/bin/env python3
"""
Hermes Transcribe - Audio transcription and formatting tool
Downloads audio from Google Drive, transcribes via OpenAI Whisper API,
and formats output in Hermes style for human verification.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime
import mimetypes
import uuid
import io
import time
import getpass

class HermesTranscriber:
    def __init__(self):
        self.api_key = None
        self.session_folder = None
        self.audio_file = None
        self.transcript_text = ""
        
    def setup_session_folder(self):
        """Create session folder on Desktop"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desktop = Path.home() / "Desktop"
        self.session_folder = desktop / f"hermes_session_{timestamp}"
        self.session_folder.mkdir(exist_ok=True)
        print(f"✅ Created session folder: {self.session_folder}")
        return self.session_folder
    
    def get_api_key(self):
        """Get OpenAI API key from environment or prompt user"""
        # Check environment variable
        api_key = os.environ.get('OPENAI_API_KEY')
        
        if api_key:
            print("✅ Using API key from environment variable")
            self.api_key = api_key
            return
        
        # Check saved key file
        key_file = Path.home() / ".openai_key"
        if key_file.exists():
            try:
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()
                if api_key:
                    print("✅ Using saved API key from ~/.openai_key")
                    self.api_key = api_key
                    return
            except Exception as e:
                print(f"⚠️  Could not read saved key: {e}")
        
        # Prompt user for key
        print("\n🔑 OpenAI API key required for transcription")
        print("   Your key will be used securely and not logged")
        api_key = getpass.getpass("Enter your OpenAI API key: ").strip()
        
        if not api_key:
            print("❌ No API key provided. Exiting.")
            sys.exit(1)
        
        # Ask to save key
        save = input("\nSave API key for future use? (y/n): ").lower()
        if save == 'y':
            try:
                key_file.write_text(api_key)
                key_file.chmod(0o600)  # Secure permissions
                print(f"✅ API key saved to {key_file}")
                print("   ⚠️  Security reminder: Protect this file and never share your API key")
            except Exception as e:
                print(f"⚠️  Could not save key: {e}")
        
        self.api_key = api_key
    
    def download_from_gdrive(self):
        """Download audio file from Google Drive using curl"""
        file_id = "1R18WHCYcCgdHDyggJ0r2EC69FJ9Ww08z"
        filename = "2025-07-29--0901.m4a"
        self.audio_file = self.session_folder / filename
        
        print(f"\n📥 Downloading audio file from Google Drive...")
        print(f"   File: {filename}")
        
        # Google Drive direct download URL
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Use curl to download (handles redirects better)
        cmd = [
            "curl", "-L", "-o", str(self.audio_file),
            "--progress-bar",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # Try with confirmation parameter for large files
                url_confirm = f"{url}&confirm=t"
                cmd[-1] = url_confirm
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"Download failed: {result.stderr}")
            
            if self.audio_file.exists() and self.audio_file.stat().st_size > 0:
                size_mb = self.audio_file.stat().st_size / (1024 * 1024)
                print(f"✅ Downloaded {filename} ({size_mb:.1f} MB)")
            else:
                raise Exception("Downloaded file is empty or missing")
                
        except Exception as e:
            print(f"❌ Download failed: {e}")
            sys.exit(1)
    
    def create_multipart_data(self, file_path):
        """Create multipart form data for file upload"""
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Build multipart data
        parts = []
        
        # Add file field
        parts.append(f'--{boundary}'.encode())
        parts.append(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode())
        parts.append(f'Content-Type: {mimetypes.guess_type(file_path)[0] or "application/octet-stream"}'.encode())
        parts.append(b'')
        parts.append(file_data)
        
        # Add model field
        parts.append(f'--{boundary}'.encode())
        parts.append(b'Content-Disposition: form-data; name="model"')
        parts.append(b'')
        parts.append(b'whisper-1')
        
        # Add response format
        parts.append(f'--{boundary}'.encode())
        parts.append(b'Content-Disposition: form-data; name="response_format"')
        parts.append(b'')
        parts.append(b'verbose_json')
        
        # End boundary
        parts.append(f'--{boundary}--'.encode())
        
        # Join with CRLF
        body = b'\r\n'.join(parts)
        
        return body, f'multipart/form-data; boundary={boundary}'
    
    def transcribe_with_whisper(self):
        """Transcribe audio using OpenAI Whisper API"""
        print(f"\n🎙️  Transcribing audio with OpenAI Whisper...")
        print(f"   This may take a few minutes for a 9-minute recording...")
        
        url = "https://api.openai.com/v1/audio/transcriptions"
        
        # Create multipart data
        body, content_type = self.create_multipart_data(self.audio_file)
        
        # Create request
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {self.api_key}')
        req.add_header('Content-Type', content_type)
        req.data = body
        
        try:
            # Make request with timeout
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode())
                
            if 'text' in result:
                self.transcript_text = result['text']
                word_count = len(self.transcript_text.split())
                print(f"✅ Transcription complete ({word_count} words)")
                
                # Save raw transcript
                raw_file = self.session_folder / "raw_transcript.txt"
                raw_file.write_text(self.transcript_text)
                print(f"   Saved raw transcript to {raw_file.name}")
                
                # Save full JSON response if available
                if 'segments' in result:
                    json_file = self.session_folder / "transcript_details.json"
                    with open(json_file, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"   Saved detailed transcript to {json_file.name}")
                    
            else:
                raise Exception("No transcript in response")
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"❌ API Error: {e.code} - {error_body}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            sys.exit(1)
    
    def format_hermes_markdown(self):
        """Create formatted markdown file in Hermes style"""
        print(f"\n📝 Formatting transcript in Hermes style...")
        
        # Get metadata
        now = datetime.now()
        word_count = len(self.transcript_text.split())
        char_count = len(self.transcript_text)
        
        # Create markdown content
        markdown = f"""# Hermes Transcript Session
**Generated**: {now.strftime('%Y-%m-%d %H:%M:%S')}  
**Source File**: 2025-07-29--0901.m4a  
**Meeting Date**: July 29, 2025  
**Duration**: ~9 minutes  
**Word Count**: {word_count:,}  
**Character Count**: {char_count:,}  

---

## 📋 Raw Transcript

{self.transcript_text}

---

## 👥 Speaker Identification

*Please identify speakers and mark with checkboxes when verified:*

- [ ] Speaker 1: _________________
- [ ] Speaker 2: _________________
- [ ] Speaker 3: _________________
- [ ] Speaker 4: _________________

### Speaker Notes
_Add any notes about speaker identification, voice characteristics, or context:_

---

## ✅ Action Items

*Extract and verify action items from the transcript:*

| Status | Action Item | Owner | Due Date | Priority |
|--------|------------|-------|----------|----------|
| ⬜ | | | | |
| ⬜ | | | | |
| ⬜ | | | | |
| ⬜ | | | | |
| ⬜ | | | | |

### Action Item Notes
_Additional context or dependencies:_

---

## 🎯 Key Decisions

*Document important decisions made during the meeting:*

1. **Decision**: 
   - **Context**: 
   - **Rationale**: 
   - **Impact**: 

2. **Decision**: 
   - **Context**: 
   - **Rationale**: 
   - **Impact**: 

3. **Decision**: 
   - **Context**: 
   - **Rationale**: 
   - **Impact**: 

---

## 🔄 Follow-ups Required

*List items requiring follow-up or further discussion:*

| Item | Type | Assigned To | Target Date | Status |
|------|------|-------------|-------------|---------|
| | Research | | | Pending |
| | Discussion | | | Pending |
| | Approval | | | Pending |
| | Implementation | | | Pending |

### Follow-up Notes
_Dependencies, blockers, or additional context:_

---

## 📊 Meeting Analytics

- **Topics Discussed**: _List main topics_
- **Participants**: _List all participants_
- **Meeting Type**: _Stand-up / Planning / Review / Other_
- **Overall Sentiment**: _Positive / Neutral / Concerns_
- **Next Meeting**: _Date/time if scheduled_

---

## 🔐 Security & Privacy Notes

⚠️ **Before uploading to task management systems:**
- [ ] Verify no sensitive information is exposed
- [ ] Confirm all speaker attributions are correct
- [ ] Check that action items are accurately captured
- [ ] Ensure compliance with any NDAs or confidentiality agreements

---

## 📁 Session Information

**Session Folder**: `{self.session_folder.name}`  
**Files Generated**:
- `2025-07-29--0901.m4a` - Original audio file
- `raw_transcript.txt` - Unformatted transcript text
- `hermes_formatted.md` - This formatted document
- `transcript_details.json` - Detailed transcription data (if available)

**Processing Details**:
- Transcription Model: OpenAI Whisper-1
- Processing Time: {now.strftime('%Y-%m-%d %H:%M:%S')}
- Platform: macOS / Python {sys.version.split()[0]}

---

*Generated by Hermes Transcribe v1.0 - Human verification required before system upload*
"""
        
        # Save markdown file
        md_file = self.session_folder / "hermes_formatted.md"
        md_file.write_text(markdown)
        print(f"✅ Created formatted document: {md_file.name}")
        
        return md_file
    
    def open_in_finder(self):
        """Open session folder in Finder"""
        try:
            subprocess.run(["open", str(self.session_folder)])
            print(f"\n✅ Opened session folder in Finder")
        except Exception as e:
            print(f"⚠️  Could not open Finder: {e}")
    
    def run(self):
        """Main execution flow"""
        print("🚀 Hermes Transcribe - Starting session")
        print("=" * 50)
        
        # Setup
        self.setup_session_folder()
        self.get_api_key()
        
        # Download
        self.download_from_gdrive()
        
        # Transcribe
        self.transcribe_with_whisper()
        
        # Format
        self.format_hermes_markdown()
        
        # Complete
        print("\n" + "=" * 50)
        print("✨ Session complete!")
        print(f"📁 All files saved to: {self.session_folder}")
        print("\n⚠️  IMPORTANT: Please review and verify:")
        print("   1. Speaker identification")
        print("   2. Action items extraction")
        print("   3. Key decisions and follow-ups")
        print("   4. Remove any sensitive information")
        print("\n   Then upload to your task management system.")
        
        # Open folder
        self.open_in_finder()

def main():
    """Entry point"""
    try:
        transcriber = HermesTranscriber()
        transcriber.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()