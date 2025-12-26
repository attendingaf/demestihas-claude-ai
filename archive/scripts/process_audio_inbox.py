#!/usr/bin/env python3
"""
Process all audio files in Audio-Inbox directory
"""

import os
import sys
import subprocess
import glob

def process_audio_file(audio_file):
    """Process a single audio file"""
    
    filename = os.path.basename(audio_file)
    size_mb = os.path.getsize(audio_file) / (1024 * 1024)
    
    print(f"\n{'='*60}")
    print(f"📁 Processing: {filename} ({size_mb:.1f} MB)")
    print('='*60)
    
    # Upload to VPS
    print(f"📤 Uploading to VPS...")
    cmd = ["scp", audio_file, "root@178.156.170.161:/tmp/"]
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"❌ Failed to upload {filename}")
        return False
    
    print(f"✅ Uploaded: /tmp/{filename}")
    
    # Process on VPS
    print("🎯 Processing on VPS...")
    ssh_cmd = f"""
    cd /root/lyco-ai
    
    FILE="/tmp/{filename}"
    
    # Set OpenAI API key
    if [ -f /root/lyco-ai/.env ]; then
        export $(grep OPENAI_API_KEY /root/lyco-ai/.env | xargs)
    fi
    
    # Check if quick_transcribe.py exists
    if [ ! -f quick_transcribe.py ]; then
        echo "Creating quick_transcribe.py..."
        cat > quick_transcribe.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def transcribe_audio(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found")
        return None
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"Transcribing {{file_size:.1f}}MB file...")
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript
    except Exception as e:
        print(f"Error: {{e}}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_transcribe.py <file>")
        sys.exit(1)
    
    transcript = transcribe_audio(sys.argv[1])
    if transcript:
        output_file = sys.argv[1].rsplit('.', 1)[0] + '_transcript.txt'
        with open(output_file, 'w') as f:
            f.write(transcript)
        print(f"Saved to: {{output_file}}")
        print("\\n--- TRANSCRIPT PREVIEW ---")
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
EOF
    fi
    
    # Transcribe
    echo "🎤 Transcribing with OpenAI Whisper..."
    python3 quick_transcribe.py "$FILE"
    
    # Copy transcript to known location
    TRANSCRIPT="${{FILE%.mp3}}_transcript.txt"
    if [ -f "$TRANSCRIPT" ]; then
        cp "$TRANSCRIPT" "/tmp/{filename%.mp3}_transcript.txt"
        echo "✅ Transcript saved: /tmp/{filename%.mp3}_transcript.txt"
        echo ""
        echo "--- PREVIEW ---"
        head -20 "$TRANSCRIPT"
    fi
    """
    
    result = subprocess.run(["ssh", "root@178.156.170.161", ssh_cmd])
    
    # Download transcript back
    print(f"\n📥 Downloading transcript...")
    transcript_remote = f"/tmp/{filename.replace('.mp3', '_transcript.txt')}"
    transcript_local = f"Audio-Inbox/{filename.replace('.mp3', '_transcript.txt')}"
    
    subprocess.run(["scp", f"root@178.156.170.161:{transcript_remote}", transcript_local])
    
    if os.path.exists(transcript_local):
        print(f"✅ Transcript saved locally: {transcript_local}")
    
    return True

def main():
    print("🎙️ Audio Inbox Processor")
    print("=" * 60)
    
    audio_dir = "Audio-Inbox"
    
    # Find all MP3 files
    audio_files = glob.glob(os.path.join(audio_dir, "*.mp3"))
    
    if not audio_files:
        print(f"❌ No MP3 files found in {audio_dir}")
        return
    
    print(f"📂 Found {len(audio_files)} audio files:")
    for f in audio_files:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"  • {os.path.basename(f)} ({size_mb:.1f} MB)")
    
    # Process each file
    for audio_file in audio_files:
        process_audio_file(audio_file)
    
    print("\n" + "="*60)
    print("✅ All files processed!")
    print("="*60)
    print("\nTranscripts saved in Audio-Inbox/")
    print("\nTo view a transcript:")
    print("cat Audio-Inbox/*_transcript.txt")

if __name__ == "__main__":
    main()
