#!/usr/bin/env python3
"""
Direct audio processor - skip Google Drive download, work with local file
"""

import os
import sys
import subprocess

def upload_and_process(local_file):
    """Upload local file to VPS and process it"""
    
    if not os.path.exists(local_file):
        print(f"❌ File not found: {local_file}")
        print("\nPlease provide the path to your audio file")
        return False
    
    # Get file info
    filename = os.path.basename(local_file)
    size_mb = os.path.getsize(local_file) / (1024 * 1024)
    print(f"📁 Found file: {filename} ({size_mb:.1f} MB)")
    
    # Upload to VPS
    print(f"\n📤 Uploading to VPS...")
    cmd = ["scp", local_file, "root@178.156.170.161:/tmp/"]
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("❌ Upload failed")
        return False
    
    print(f"✅ Uploaded to VPS: /tmp/{filename}")
    
    # Copy quick_transcribe.py to VPS first
    print("\n📋 Setting up transcription script on VPS...")
    local_script = os.path.expanduser("~/Projects/demestihas-ai/quick_transcribe.py")
    if os.path.exists(local_script):
        subprocess.run(["scp", local_script, "root@178.156.170.161:/root/lyco-ai/"])
    
    # Process on VPS
    print("\n🎯 Processing on VPS...")
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
    
    # Check if we need to compress
    FILE_SIZE_BYTES=$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE" 2>/dev/null)
    if [ "$FILE_SIZE_BYTES" -gt 26214400 ]; then
        echo "File is over 25MB, compressing for Whisper API..."
        ffmpeg -i "$FILE" -ac 1 -ar 16000 -b:a 32k "/tmp/compressed.mp3" -y
        FILE="/tmp/compressed.mp3"
        echo "Compressed to: $(du -h "$FILE" | cut -f1)"
    fi
    
    # Set OpenAI API key from .env
    if [ -f /root/lyco-ai/.env ]; then
        export $(grep OPENAI_API_KEY /root/lyco-ai/.env | xargs)
    fi
    
    # Transcribe
    echo ""
    echo "🎤 Transcribing with OpenAI Whisper..."
    python3 quick_transcribe.py "$FILE"
    
    # Show result
    TRANSCRIPT="${{FILE%.mp3}}_transcript.txt"
    if [ -f "$TRANSCRIPT" ]; then
        echo ""
        echo "✅ TRANSCRIPTION COMPLETE!"
        echo "================================"
        echo "First 50 lines of transcript:"
        echo "================================"
        head -50 "$TRANSCRIPT"
        echo ""
        echo "================================"
        echo "Full transcript saved at: $TRANSCRIPT"
        echo ""
        # Also save to a known location
        cp "$TRANSCRIPT" "/tmp/latest_transcript.txt"
        echo "Also copied to: /tmp/latest_transcript.txt"
    else
        echo "❌ Transcription failed - checking for errors..."
        echo "Trying direct OpenAI call..."
        python3 -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
with open('$FILE', 'rb') as audio:
    transcript = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio,
        response_format='text'
    )
    print(transcript)
    with open('/tmp/latest_transcript.txt', 'w') as f:
        f.write(transcript)
"
    fi
    """
    
    result = subprocess.run(["ssh", "root@178.156.170.161", ssh_cmd])
    
    print("\n" + "="*50)
    print("📋 To retrieve the transcript:")
    print("="*50)
    print("scp root@178.156.170.161:/tmp/latest_transcript.txt ./my_transcript.txt")
    print("\nOr view it directly on VPS:")
    print("ssh root@178.156.170.161 'cat /tmp/latest_transcript.txt'")
    
    return True

def main():
    print("🎙️ Direct Audio Processor")
    print("=" * 40)
    
    # Check if file was provided as argument
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # Try known locations
        possible_files = [
            "/tmp/Audio_08_22_2025_12_01_43.mp3",
            "~/Downloads/Audio_08_22_2025_12_01_43.mp3",
            "./Audio_08_22_2025_12_01_43.mp3",
        ]
        
        audio_file = None
        for f in possible_files:
            expanded = os.path.expanduser(f)
            if os.path.exists(expanded):
                audio_file = expanded
                break
        
        if not audio_file:
            print("\n❌ No audio file found!")
            print("\nUsage: python3 gdrive_processor.py [path_to_audio_file]")
            print("\nExample: python3 gdrive_processor.py ~/Downloads/Audio_08_22_2025_12_01_43.mp3")
            return
    
    upload_and_process(audio_file)

if __name__ == "__main__":
    main()
