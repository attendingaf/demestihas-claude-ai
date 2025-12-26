#!/usr/bin/env python3
"""
Complete audio processing pipeline for Google Drive files
Downloads from Drive, uploads to VPS, and processes
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def download_from_drive(file_id, output_path):
    """Download file from Google Drive using multiple methods"""
    
    # Method 1: Try with gdown
    try:
        import gdown
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, output_path, quiet=False)
        if os.path.exists(output_path):
            return True
    except ImportError:
        print("gdown not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gdown"])
        try:
            import gdown
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, output_path, quiet=False)
            if os.path.exists(output_path):
                return True
        except:
            pass
    
    # Method 2: Try with requests
    try:
        import requests
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, stream=True)
        
        # Check for virus scan warning
        if "virus scan warning" in response.text.lower():
            # Extract confirm token
            for line in response.text.split('\n'):
                if 'confirm=' in line:
                    confirm = line.split('confirm=')[1].split('"')[0]
                    download_url = f"https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}"
                    response = requests.get(download_url, stream=True)
                    break
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
    except:
        pass
    
    return False

def upload_to_vps(local_file, vps_path="/tmp/"):
    """Upload file to VPS using scp"""
    filename = os.path.basename(local_file)
    remote_path = f"root@178.156.170.161:{vps_path}{filename}"
    
    print(f"\n📤 Uploading {filename} to VPS...")
    result = subprocess.run(
        ["scp", local_file, remote_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ Uploaded to VPS: {vps_path}{filename}")
        return f"{vps_path}{filename}"
    else:
        print(f"❌ Upload failed: {result.stderr}")
        return None

def process_on_vps(remote_file):
    """Process audio file on VPS"""
    filename = os.path.basename(remote_file)
    
    print(f"\n🎯 Processing {filename} on VPS...")
    
    # Create processing script
    process_script = f"""
cd /root/lyco-ai

# Check if file exists
if [ ! -f "{remote_file}" ]; then
    echo "Error: File not found at {remote_file}"
    exit 1
fi

# Get file size
FILE_SIZE=$(du -h "{remote_file}" | cut -f1)
echo "Processing file: {filename} ($FILE_SIZE)"

# Check if Hermes container is running
if docker ps | grep -q hermes_audio; then
    echo "Using Hermes audio processor..."
    cp "{remote_file}" /root/lyco-ai/hermes_audio/
    docker exec hermes_audio python process_audio.py "/app/{filename}"
elif [ -f "quick_transcribe.py" ]; then
    echo "Using quick transcribe script..."
    python3 quick_transcribe.py "{remote_file}"
elif [ -f "audio_workflow/workflow.py" ]; then
    echo "Using audio workflow..."
    cp "{remote_file}" /root/lyco-ai/audio_workflow/
    cd audio_workflow
    python3 workflow.py --file "{filename}"
else
    echo "No audio processing method available!"
    echo "Transcribing with OpenAI directly..."
    python3 -c "
import openai
import os
openai.api_key = os.getenv('OPENAI_API_KEY')
with open('{remote_file}', 'rb') as f:
    transcript = openai.Audio.transcribe('whisper-1', f)
    print(transcript['text'])
    with open('{remote_file}_transcript.txt', 'w') as out:
        out.write(transcript['text'])
"
fi
"""
    
    # Execute on VPS
    result = subprocess.run(
        ["ssh", "root@178.156.170.161", process_script],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Errors: {result.stderr}")
    
    return result.returncode == 0

def main():
    # Your Google Drive file
    FILE_ID = "1bmpO9OPTzcGmqRLKzAFAF8OnbIglKV2Z"
    FILE_NAME = "Audio_08_22_2025_12_01_43.mp3"
    
    print("🎙️ Google Drive Audio Processing Pipeline")
    print("=" * 50)
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        local_file = os.path.join(tmpdir, FILE_NAME)
        
        # Step 1: Download from Drive
        print(f"\n📥 Downloading from Google Drive...")
        print(f"File ID: {FILE_ID}")
        
        if download_from_drive(FILE_ID, local_file):
            file_size = os.path.getsize(local_file) / (1024 * 1024)  # MB
            print(f"✅ Downloaded: {FILE_NAME} ({file_size:.1f} MB)")
            
            # Step 2: Upload to VPS
            remote_path = upload_to_vps(local_file)
            
            if remote_path:
                # Step 3: Process on VPS
                if process_on_vps(remote_path):
                    print("\n✅ Audio processing complete!")
                    print(f"\nCheck VPS for results:")
                    print(f"ssh root@178.156.170.161")
                    print(f"ls -la /tmp/*transcript*")
                else:
                    print("\n⚠️ Processing had issues. Check VPS manually.")
            else:
                print("\n❌ Failed to upload to VPS")
        else:
            print("\n❌ Failed to download from Google Drive")
            print("\nTry manual download:")
            print(f"1. Open: https://drive.google.com/file/d/{FILE_ID}/view")
            print(f"2. Click Download button")
            print(f"3. Save as: {FILE_NAME}")
            print(f"4. Run: scp {FILE_NAME} root@178.156.170.161:/tmp/")

if __name__ == "__main__":
    main()
