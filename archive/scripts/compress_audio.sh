#!/bin/bash
# Quick audio compression script for Gmail compatibility

if [ "$#" -ne 1 ]; then
    echo "Usage: ./compress_audio.sh your_audio_file.m4a"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${INPUT_FILE%.*}_compressed.mp3"

echo "Compressing $INPUT_FILE..."

# Aggressive compression to fit under 25MB
# Mono, 32kbps, 16kHz sampling - perfect for speech
ffmpeg -i "$INPUT_FILE" \
    -ac 1 \
    -ar 16000 \
    -b:a 32k \
    "$OUTPUT_FILE" \
    -y

ORIGINAL_SIZE=$(du -h "$INPUT_FILE" | cut -f1)
NEW_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo "✅ Compressed from $ORIGINAL_SIZE to $NEW_SIZE"
echo "📧 Ready to email: $OUTPUT_FILE"
echo ""
echo "Now email $OUTPUT_FILE to hermesaudio444@gmail.com"
