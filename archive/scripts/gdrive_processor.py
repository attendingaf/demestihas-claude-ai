#!/usr/bin/env python3
"""
Simple script to download audio from Google Drive and process on VPS
"""

import os
import sys
import subprocess

def install_gdown():
    """Install gdown if not available"""
    print("📦 Installing gdown...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "gdown"], 
                   capture_output=True)
    print("✅ gdown installed")

def download_file(file_id, output_name):
    """Download file from Google Drive"""
    try:
        import gdown
    except ImportError:
        install_gdown()
        import gdown
    
    url = f"https://drive.google.com/uc?id={file_id}"
    output_path = f"/tmp/{output_name}"
    
    print(f"📥 Downloading from Google Drive...")
    print(f"URL: {url}")
    print(f"Saving to: {output_path}")
    
    try:
        gdown.download(url, output_path, quiet=False)
        
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Downloaded: {output_name} ({size_mb:.1f} MB)")
            return output_path
    except Exception as e:
        print(f"❌ Download error: {e}")
    
    return None

def upload_to_vps(local_file):
    """Upload file to VPS"""
    print(f"\n📤 Uploading to VPS...")
    cmd = ["scp", local_file, "root@178.156.170.161:/tmp/"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Uploaded to VPS: /tmp/{os.path.basename(local_file)}")
        return True
    else:
        print(f"❌ Upload failed: {result.stderr}")
        return False

def process_on_vps(filename):
    """Process audio on VPS"""
    print(f"\n🎯 Processing on VPS...")
    
    # First, copy quick_transcribe.py to VPS if it doesn't exist
    local_script = os.path.expanduser("~/Projects/demestihas-ai/quick_transcribe.py")
    if os.path.exists(local_script):
        print("Copying quick_transcribe.py to VPS...")
        subprocess.run(["scp", local_script, "root@178.156.170.161:/root/lyco-ai/"], 
                      capture_output=True)
    
    # SSH command to process the file
    ssh_cmd = f"""
    cd /root/lyco-ai
    
    # Check file
    FILE="/tmp/{filename}"
    if [ ! -f "$FILE" ]; then
        echo "Error: File not found at $FILE"
        exit 1
    fi
    
    # Get file size
    FILE_SIZE=$(du -h "$FILE" | cut -f1)
    echo "Processing: $FILE ($FILE_SIZE)"
    
    # Compress if needed
    FILE_SIZE_BYTES=$(stat -c%s "$FILE")
    if [ $FILE_SIZE_BYTES -gt 26214400 ]; then
        echo "Compressing audio (file is over 25MB)..."
        ffmpeg -i "$FILE" -ac 1 -ar 16000 -b:a 32k "/tmp/compressed.mp3" -y
        FILE="/tmp/compressed.mp3"
    fi
    
    # Transcribe
    echo "Transcribing with OpenAI Whisper..."
    python3 quick_transcribe.py "$FILE"
    
    # Show result
    TRANSCRIPT="${{FILE%.mp3}}_transcript.txt"
    if [ -f "$TRANSCRIPT" ]; then
        echo ""
        echo "✅ TRANSCRIPTION COMPLETE!"
        echo "================================"
        head -30 "$TRANSCRIPT"
        echo "..."
        echo "================================"
        echo "Full transcript at: $TRANSCRIPT"
    else
        echo "❌ Transcription failed"
    fi
    """
    
    result = subprocess.run(["ssh", "root@178.156.170.161", ssh_cmd], 
                           capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Errors: {result.stderr}")

def main():
    FILE_ID = "1bmpO9OPTzcGmqRLKzAFAF8OnbIglKV2Z"
    FILE_NAME = "Audio_08_22_2025_12_01_43.mp3"
    
    print("🎙️ Google Drive Audio Processor")
    print("=" * 40)
    
    # Download
    local_file = download_file(FILE_ID, FILE_NAME)
    
    if local_file:
        # Upload
        if upload_to_vps(local_file):
            # Process
            process_on_vps(FILE_NAME)
            
            print("\n📋 To get the transcript locally:")
            print("scp root@178.156.170.161:/tmp/*transcript.txt .")
    else:
        print("\n❌ Could not download file from Google Drive")
        print("\nTry manual download:")
        print(f"1. Go to: https://drive.google.com/file/d/{FILE_ID}/view")
        print(f"2. Click Download")
        print(f"3. Save the file")
        print(f"4. Run: scp YOUR_FILE.mp3 root@178.156.170.161:/tmp/")
        print(f"5. SSH to VPS and run: python3 /root/lyco-ai/quick_transcribe.py /tmp/YOUR_FILE.mp3")

if __name__ == "__main__":
    main()
