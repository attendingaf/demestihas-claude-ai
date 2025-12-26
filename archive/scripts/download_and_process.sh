#!/bin/bash
# Simple script to download your audio and process it

FILE_ID="1bmpO9OPTzcGmqRLKzAFAF8OnbIglKV2Z"
FILE_NAME="Audio_08_22_2025_12_01_43.mp3"

echo "🎙️ Audio Processing Pipeline"
echo "============================"
echo ""

# Step 1: Install gdown if needed
echo "📦 Checking for gdown..."
if ! command -v gdown &> /dev/null; then
    echo "Installing gdown..."
    pip3 install gdown
fi

# Step 2: Download from Google Drive
echo ""
echo "📥 Downloading from Google Drive..."
cd /tmp
gdown "https://drive.google.com/uc?id=${FILE_ID}" -O "${FILE_NAME}"

# Step 3: Check if download succeeded
if [ -f "${FILE_NAME}" ]; then
    FILE_SIZE=$(du -h "${FILE_NAME}" | cut -f1)
    echo "✅ Downloaded successfully: ${FILE_SIZE}"
    
    # Step 4: Upload to VPS
    echo ""
    echo "📤 Uploading to VPS..."
    scp "${FILE_NAME}" root@178.156.170.161:/tmp/
    
    # Step 5: Process on VPS
    echo ""
    echo "🎯 Processing on VPS..."
    ssh root@178.156.170.161 << 'ENDSSH'
cd /root/lyco-ai

# Check file size
FILE_SIZE=$(du -h /tmp/Audio_08_22_2025_12_01_43.mp3 | cut -f1)
echo "File on VPS: /tmp/Audio_08_22_2025_12_01_43.mp3 (${FILE_SIZE})"

# If file is over 25MB, compress it
FILE_SIZE_BYTES=$(stat -c%s /tmp/Audio_08_22_2025_12_01_43.mp3)
if [ $FILE_SIZE_BYTES -gt 26214400 ]; then
    echo "File is large, compressing..."
    ffmpeg -i /tmp/Audio_08_22_2025_12_01_43.mp3 \
        -ac 1 -ar 16000 -b:a 32k \
        /tmp/audio_compressed.mp3 -y
    PROCESS_FILE="/tmp/audio_compressed.mp3"
else
    PROCESS_FILE="/tmp/Audio_08_22_2025_12_01_43.mp3"
fi

# Try to process with available methods
if [ -f "quick_transcribe.py" ]; then
    echo ""
    echo "🎤 Transcribing with OpenAI Whisper..."
    python3 quick_transcribe.py "$PROCESS_FILE"
    
    # Check for transcript
    if [ -f "${PROCESS_FILE}_transcript.txt" ]; then
        echo ""
        echo "✅ Transcription complete!"
        echo ""
        echo "--- TRANSCRIPT PREVIEW ---"
        head -20 "${PROCESS_FILE}_transcript.txt"
        echo "..."
        echo ""
        echo "Full transcript saved to: ${PROCESS_FILE}_transcript.txt"
    fi
else
    echo "quick_transcribe.py not found, trying direct OpenAI call..."
    python3 << 'PYTHON'
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
audio_file = open("/tmp/audio_compressed.mp3", "rb") if os.path.exists("/tmp/audio_compressed.mp3") else open("/tmp/Audio_08_22_2025_12_01_43.mp3", "rb")

transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    response_format="text"
)

print(transcript)
with open("/tmp/transcript.txt", "w") as f:
    f.write(transcript)
print("\nTranscript saved to /tmp/transcript.txt")
PYTHON
fi
ENDSSH
    
    echo ""
    echo "✅ Processing complete!"
    echo ""
    echo "To retrieve the transcript from VPS:"
    echo "scp root@178.156.170.161:/tmp/*transcript.txt ."
    
else
    echo "❌ Download failed. Please check your internet connection and try again."
    echo ""
    echo "Alternative: Download manually from:"
    echo "https://drive.google.com/file/d/${FILE_ID}/view"
fi
