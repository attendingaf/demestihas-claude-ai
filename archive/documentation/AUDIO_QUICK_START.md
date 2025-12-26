# Audio Workflow Quick Deployment Guide

## Prerequisites Checklist

- [ ] VPS access (178.156.170.161)
- [ ] Google Cloud service account with Drive API enabled
- [ ] OpenAI API key
- [ ] Anthropic API key  
- [ ] Supabase project (URL and anon key)

## Step 1: Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable Google Drive API
4. Create service account:
   - IAM & Admin → Service Accounts → Create
   - Name: "audio-workflow-processor"
   - Grant role: "Editor"
   - Create key (JSON) → Download

5. Share your Google Drive folder with service account email:
   - Find email in JSON (e.g., `audio-workflow@project.iam.gserviceaccount.com`)
   - Share folder: https://drive.google.com/drive/folders/1HuuRO8xMgCksqxf5Aj_-EWVMJJTR9sj7
   - Give "Editor" permissions

## Step 2: Quick VPS Setup

```bash
# SSH to VPS
ssh root@178.156.170.161

# Create directories
mkdir -p /root/lyco-ai/audio_workflow
mkdir -p /root/lyco-ai/credentials

# Install FFmpeg (if not installed)
apt-get update && apt-get install -y ffmpeg

# Create .env file
cat > /root/lyco-ai/.env << 'EOF'
# Google Drive
GOOGLE_DRIVE_FOLDER_ID="1HuuRO8xMgCksqxf5Aj_-EWVMJJTR9sj7"
GOOGLE_SERVICE_ACCOUNT_PATH="/app/credentials/google-service-account.json"

# OpenAI
OPENAI_API_KEY="sk-..."

# Anthropic
ANTHROPIC_API_KEY="sk-ant-..."

# Supabase
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
EOF

# Edit to add your actual keys
nano /root/lyco-ai/.env
```

## Step 3: Upload Service Account JSON

From your local machine:
```bash
scp ~/Downloads/your-service-account.json root@178.156.170.161:/root/lyco-ai/credentials/google-service-account.json
```

## Step 4: Create Minimal Working Version

For immediate use, here's a simplified standalone version:

```bash
# On VPS, create standalone script
cat > /root/lyco-ai/quick_audio_processor.py << 'EOF'
#!/usr/bin/env python3
"""
Minimal audio processor - upload audio to Drive folder, get transcript and analysis
"""

import os
import sys
import subprocess
from pathlib import Path
from openai import OpenAI
from anthropic import Anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from datetime import datetime

# Configuration
FOLDER_ID = "1HuuRO8xMgCksqxf5Aj_-EWVMJJTR9sj7"
WORK_DIR = Path("/tmp/audio_work")
WORK_DIR.mkdir(exist_ok=True)

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    '/root/lyco-ai/credentials/google-service-account.json',
    scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=creds)

def check_for_audio_files():
    """Get list of audio files from Drive folder"""
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, size)"
    ).execute()
    return results.get('files', [])

def download_file(file_id, file_name):
    """Download file from Drive"""
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    output_path = WORK_DIR / file_name
    with open(output_path, 'wb') as f:
        f.write(fh.getvalue())
    return output_path

def compress_audio(input_path):
    """Compress to mono 16kHz"""
    output_path = WORK_DIR / f"compressed_{input_path.name}"
    cmd = [
        'ffmpeg', '-i', str(input_path),
        '-ac', '1', '-ar', '16000', '-b:a', '32k',
        '-y', str(output_path)
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path

def transcribe(audio_path):
    """Transcribe using Whisper"""
    with open(audio_path, 'rb') as f:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text"
        )
    return transcript

def analyze_meeting(transcript):
    """Analyze with Claude"""
    prompt = f"""Analyze this meeting transcript:

1. What happened (summary)
2. What was really being said (subtext)
3. Surprises
4. Objectives accomplished vs not
5. What could be better

Transcript:
{transcript}

Provide a structured analysis:"""

    response = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def main():
    print("🎙️ Audio Workflow Processor")
    print(f"Monitoring folder: {FOLDER_ID}")
    
    # Get audio files
    files = check_for_audio_files()
    if not files:
        print("No audio files found")
        return
    
    print(f"Found {len(files)} audio files")
    
    for file_info in files[:1]:  # Process first file only
        print(f"\nProcessing: {file_info['name']}")
        
        # Download
        print("1. Downloading...")
        audio_path = download_file(file_info['id'], file_info['name'])
        
        # Compress
        print("2. Compressing...")
        compressed = compress_audio(audio_path)
        
        # Check size
        size_mb = os.path.getsize(compressed) / (1024*1024)
        print(f"   Size: {size_mb:.1f}MB")
        
        if size_mb > 25:
            print("   WARNING: File >25MB, needs chunking")
            # Add chunking logic here if needed
        
        # Transcribe
        print("3. Transcribing...")
        transcript = transcribe(compressed)
        print(f"   Words: {len(transcript.split())}")
        
        # Save transcript
        transcript_file = WORK_DIR / f"{file_info['name']}_transcript.txt"
        with open(transcript_file, 'w') as f:
            f.write(transcript)
        print(f"   Saved: {transcript_file}")
        
        # Analyze
        print("4. Analyzing...")
        analysis = analyze_meeting(transcript)
        
        # Save analysis
        analysis_file = WORK_DIR / f"{file_info['name']}_analysis.md"
        with open(analysis_file, 'w') as f:
            f.write(f"# Analysis: {file_info['name']}\n\n")
            f.write(f"Date: {datetime.now()}\n\n")
            f.write(analysis)
        print(f"   Saved: {analysis_file}")
        
        print("\n✅ Complete!")
        print(f"Results in: {WORK_DIR}")

if __name__ == "__main__":
    main()
EOF

chmod +x /root/lyco-ai/quick_audio_processor.py
```

## Step 5: Install Python Dependencies

```bash
# On VPS
pip install openai anthropic google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Step 6: Test Run

```bash
# Load environment variables
export $(cat /root/lyco-ai/.env | xargs)

# Run processor
python /root/lyco-ai/quick_audio_processor.py
```

## Step 7: Full System Deployment (Later)

Once the quick version works, deploy the full system:

```bash
# Copy all module files from handoffs 004 and 005
# Build Docker image
# Run with docker-compose
```

## Troubleshooting

1. **"No audio files found"**
   - Check folder ID is correct
   - Verify service account has access to folder
   - Check files are audio MIME type

2. **"FFmpeg not found"**
   - Install: `apt-get install ffmpeg`

3. **"API key invalid"**
   - Check .env file has correct keys
   - Verify keys are active in respective dashboards

4. **File >25MB warning**
   - Manually chunk or use full system with auto-chunking

## Output Locations

- Local temp: `/tmp/audio_work/`
- Transcripts: `*_transcript.txt`
- Analysis: `*_analysis.md`

For production, outputs will auto-upload to Google Drive folders.
