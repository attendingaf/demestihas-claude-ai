#!/bin/bash
# Script to download Google Drive audio file and process on VPS

# Google Drive file ID from your URL
FILE_ID="1bmpO9OPTzcGmqRLKzAFAF8OnbIglKV2Z"
OUTPUT_FILE="Audio_08_22_2025_12_01_43.mp3"

echo "📥 Downloading audio file from Google Drive..."
echo ""

# Method 1: Using gdown (if installed)
if command -v gdown &> /dev/null; then
    echo "Using gdown to download..."
    gdown "https://drive.google.com/uc?id=${FILE_ID}" -O "${OUTPUT_FILE}"
else
    echo "gdown not found. Installing it first..."
    pip install gdown --quiet
    gdown "https://drive.google.com/uc?id=${FILE_ID}" -O "${OUTPUT_FILE}"
fi

# Check if download succeeded
if [ -f "${OUTPUT_FILE}" ]; then
    FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    echo "✅ Downloaded: ${OUTPUT_FILE} (${FILE_SIZE})"
    echo ""
    
    # Upload to VPS
    echo "📤 Uploading to VPS..."
    scp "${OUTPUT_FILE}" root@178.156.170.161:/tmp/
    
    echo ""
    echo "🎯 File uploaded to VPS at /tmp/${OUTPUT_FILE}"
    echo ""
    echo "Now SSH to your VPS and run:"
    echo "----------------------------------------"
    echo "ssh root@178.156.170.161"
    echo "cd /root/lyco-ai"
    echo ""
    echo "# Option 1: Process with Hermes (if container is running)"
    echo "cp /tmp/${OUTPUT_FILE} /root/lyco-ai/hermes_audio/"
    echo "docker exec hermes_audio python process_audio.py /app/${OUTPUT_FILE}"
    echo ""
    echo "# Option 2: Direct transcription"
    echo "python3 quick_transcribe.py /tmp/${OUTPUT_FILE}"
    echo "----------------------------------------"
else
    echo "❌ Download failed. Trying alternative method..."
    echo ""
    echo "Alternative: Use curl with cookies"
    echo "1. Open the link in browser: https://drive.google.com/file/d/${FILE_ID}/view"
    echo "2. Click 'Download' button"
    echo "3. Copy the direct download URL from browser"
    echo "4. Run: curl -L 'PASTE_URL_HERE' -o ${OUTPUT_FILE}"
fi
