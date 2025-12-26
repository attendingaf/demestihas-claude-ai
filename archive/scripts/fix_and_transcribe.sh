#!/bin/bash
# Fix OpenAI installation and transcribe audio on VPS

echo "🔧 Fixing OpenAI installation on VPS and transcribing your audio..."
echo "======================================================="

ssh root@178.156.170.161 << 'ENDSSH'
# Install OpenAI library
echo "📦 Installing OpenAI library..."
pip3 install openai

# Verify installation
python3 -c "import openai; print('✅ OpenAI installed successfully')"

# Set up environment
cd /root/lyco-ai
if [ -f .env ]; then
    export $(grep OPENAI_API_KEY .env | xargs)
    echo "✅ API key loaded from .env"
else
    echo "⚠️ No .env file found"
fi

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not set!"
    echo "Please add it to /root/lyco-ai/.env"
    exit 1
fi

# Now transcribe the audio that's already uploaded
FILE="/tmp/Audio_08_22_2025_12_01_43.mp3"

if [ ! -f "$FILE" ]; then
    echo "❌ Audio file not found at $FILE"
    exit 1
fi

echo ""
echo "📂 Found audio file: $(du -h $FILE | cut -f1)"
echo ""
echo "🎤 Transcribing with OpenAI Whisper..."
echo "======================================="

# Run transcription
python3 << 'PYTHON'
import os
from openai import OpenAI

audio_file_path = "/tmp/Audio_08_22_2025_12_01_43.mp3"
output_path = "/tmp/Audio_08_22_2025_12_01_43_transcript.txt"

# Initialize client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print(f"Processing: {audio_file_path}")

try:
    # Open and transcribe
    with open(audio_file_path, "rb") as audio_file:
        print("Calling Whisper API...")
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    
    # Save transcript
    with open(output_path, "w") as f:
        f.write(transcript)
    
    print("\n✅ TRANSCRIPTION COMPLETE!")
    print("="*50)
    print("\n--- FIRST 1000 CHARACTERS ---")
    print(transcript[:1000])
    if len(transcript) > 1000:
        print("\n... [transcript continues] ...")
    print("\n="*50)
    print(f"\nFull transcript saved to: {output_path}")
    print(f"Transcript length: {len(transcript)} characters")
    
    # Also save to alternate location
    with open("/tmp/latest_transcript.txt", "w") as f:
        f.write(transcript)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check if OPENAI_API_KEY is valid")
    print("2. Check if you have API credits")
    print("3. File might be corrupted")
PYTHON

echo ""
echo "📊 Summary:"
echo "-----------"
if [ -f "/tmp/Audio_08_22_2025_12_01_43_transcript.txt" ]; then
    LINES=$(wc -l < /tmp/Audio_08_22_2025_12_01_43_transcript.txt)
    WORDS=$(wc -w < /tmp/Audio_08_22_2025_12_01_43_transcript.txt)
    echo "✅ Transcript created successfully"
    echo "📝 Lines: $LINES"
    echo "📝 Words: $WORDS"
else
    echo "❌ Transcript file not created"
fi

ENDSSH

echo ""
echo "======================================================="
echo "📥 Downloading transcript to your local machine..."
echo "======================================================="

# Download the transcript
scp root@178.156.170.161:/tmp/Audio_08_22_2025_12_01_43_transcript.txt ./Audio-Inbox/

if [ -f "./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt" ]; then
    echo "✅ Transcript downloaded to: Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt"
    echo ""
    echo "📄 Preview of transcript:"
    echo "========================"
    head -20 ./Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt
    echo ""
    echo "To view full transcript:"
    echo "cat Audio-Inbox/Audio_08_22_2025_12_01_43_transcript.txt"
else
    echo "Download failed. Retrieve manually with:"
    echo "scp root@178.156.170.161:/tmp/Audio_08_22_2025_12_01_43_transcript.txt ./Audio-Inbox/"
fi
