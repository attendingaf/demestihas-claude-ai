#!/bin/bash
# Fixed script with proper gdown installation

FILE_ID="1bmpO9OPTzcGmqRLKzAFAF8OnbIglKV2Z"
FILE_NAME="Audio_08_22_2025_12_01_43.mp3"

echo "🎙️ Audio Processing Pipeline"
echo "============================"
echo ""

# Step 1: Install gdown properly
echo "📦 Installing gdown..."
pip3 install --user gdown
# Add to PATH for current session
export PATH="$HOME/.local/bin:$PATH"

# Verify gdown is available
if command -v gdown &> /dev/null; then
    echo "✅ gdown installed successfully"
else
    echo "Trying alternative install..."
    python3 -m pip install gdown
fi

# Step 2: Download using Python fallback if gdown CLI fails
echo ""
echo "📥 Downloading from Google Drive..."
cd /tmp

# Try gdown CLI first
if command -v gdown &> /dev/null; then
    gdown "https://drive.google.com/uc?id=${FILE_ID}" -O "${FILE_NAME}"
else
    # Use Python directly
    echo "Using Python to download..."
    python3 << PYTHON
import sys
import subprocess
subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])

import gdown
url = "https://drive.google.com/uc?id=${FILE_ID}"
output = "${FILE_NAME}"
gdown.download(url, output, quiet=False)
PYTHON
fi

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
    TRANSCRIPT_FILE="${PROCESS_FILE%.mp3}_transcript.txt"
    if [ -f "$TRANSCRIPT_FILE" ]; then
        echo ""
        echo "✅ Transcription complete!"
        echo ""
        echo "--- TRANSCRIPT PREVIEW ---"
        head -20 "$TRANSCRIPT_FILE"
        echo "..."
        echo ""
        echo "Full transcript saved to: $TRANSCRIPT_FILE"
    fi
else
    echo "quick_transcribe.py not found on VPS"
fi
ENDSSH
    
    echo ""
    echo "✅ Processing complete!"
    echo ""
    echo "To retrieve the transcript from VPS:"
    echo "scp root@178.156.170.161:/tmp/*transcript.txt ."
    
else
    echo "❌ Download failed."
    echo ""
    echo "Let's try the Python approach directly..."
    python3 ~/Projects/demestihas-ai/process_gdrive_audio.py
fi
