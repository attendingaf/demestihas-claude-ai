#!/bin/bash
# Fix OpenAI installation with proper Ubuntu 24.04 approach

echo "🔧 Installing OpenAI on Ubuntu 24.04 VPS..."
echo "======================================================="

ssh root@178.156.170.161 << 'ENDSSH'
# Method 1: Use --break-system-packages (safe for VPS)
echo "📦 Installing OpenAI library with override..."
pip3 install openai --break-system-packages

# Verify installation
python3 -c "import openai; print('✅ OpenAI installed successfully')" || {
    echo "Trying alternative method..."
    # Method 2: Use apt if available
    apt update
    apt install -y python3-pip
    python3 -m pip install openai --break-system-packages
}

# Now transcribe
cd /root/lyco-ai
export $(grep OPENAI_API_KEY .env | xargs)

echo ""
echo "🎤 Starting transcription..."
echo "======================================="

python3 << 'PYTHON'
import os
import sys

# Try to import, if fails install inline
try:
    from openai import OpenAI
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "--break-system-packages"])
    from openai import OpenAI

audio_file_path = "/tmp/Audio_08_22_2025_12_01_43.mp3"
output_path = "/tmp/Audio_08_22_2025_12_01_43_transcript.txt"

print(f"📂 Processing: {audio_file_path}")
print(f"🔑 API Key present: {bool(os.getenv('OPENAI_API_KEY'))}")

try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    with open(audio_file_path, "rb") as audio_file:
        print("📡 Calling Whisper API...")
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    
    with open(output_path, "w") as f:
        f.write(transcript)
    
    print("\n✅ TRANSCRIPTION COMPLETE!")
    print("="*50)
    print("\n--- TRANSCRIPT PREVIEW (first 1500 chars) ---")
    print(transcript[:1500])
    if len(transcript) > 1500:
        print("\n... [continues] ...")
    print("="*50)
    print(f"\nSaved to: {output_path}")
    print(f"Length: {len(transcript)} characters, ~{len(transcript.split())} words")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
PYTHON

ENDSSH

echo ""
echo "======================================================="
echo "📥 Downloading transcript..."

# Try to download
scp root@178.156.170.161:/tmp/Audio_08_22_2025_12_01_43_transcript.txt ./Audio-Inbox/ 2>/dev/null

if [ -f "./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt" ]; then
    echo "✅ SUCCESS! Transcript saved to: Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt"
    echo ""
    echo "📄 First 30 lines of transcript:"
    echo "================================"
    head -30 ./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt
    echo "================================"
    echo ""
    echo "View full transcript with:"
    echo "cat Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt"
else
    echo "⚠️ Transcript not downloaded yet. Checking if it exists on VPS..."
    ssh root@178.156.170.161 "ls -la /tmp/*transcript*"
fi
