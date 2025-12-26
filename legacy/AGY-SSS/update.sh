#!/bin/bash
echo "⚽ Updating Soccer Calendar..."
cd "$(dirname "$0")"
node src/build.js
echo "✅ Update Complete! Upload the 'public' folder to your host."
