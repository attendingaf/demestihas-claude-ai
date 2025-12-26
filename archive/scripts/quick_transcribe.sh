#!/bin/bash
# Quick audio transcription using OpenAI Whisper API via curl
# Usage: ./quick_transcribe.sh <audio_file_path>

# Set your OpenAI API key here or export OPENAI_API_KEY
API_KEY="${OPENAI_API_KEY:-YOUR_API_KEY_HERE}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <audio_file_path>"
    exit 1
fi

AUDIO_FILE="$1"

if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: File $AUDIO_FILE not found"
    exit 1
fi

# Get file size in MB
FILE_SIZE=$(du -m "$AUDIO_FILE" | cut -f1)
echo "📁 File size: ${FILE_SIZE}MB (Whisper limit: 25MB)"

if [ $FILE_SIZE -gt 25 ]; then
    echo "⚠️  Warning: File exceeds 25MB limit. Consider compressing:"
    echo "   ffmpeg -i \"$AUDIO_FILE\" -ac 1 -ar 16000 compressed.mp3"
fi

echo "🎙️ Transcribing $AUDIO_FILE..."

# Make API call
RESPONSE=$(curl -s https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@$AUDIO_FILE" \
  -F model="whisper-1")

# Check for errors
if echo "$RESPONSE" | grep -q "error"; then
    echo "❌ Error: $RESPONSE"
    exit 1
fi

# Save transcript
OUTPUT_FILE="${AUDIO_FILE%.*}_transcript.txt"
echo "$RESPONSE" > "$OUTPUT_FILE"

echo "✅ Transcription saved to: $OUTPUT_FILE"
echo ""
echo "--- PREVIEW ---"
head -n 10 "$OUTPUT_FILE"
