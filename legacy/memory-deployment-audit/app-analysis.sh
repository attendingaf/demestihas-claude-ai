#!/bin/bash

echo "=== ANALYZING CURRENT STREAMLIT APP ===" > app-structure-report.txt
echo "" >> app-structure-report.txt

# Get app.py structure
echo "File: /root/streamlit/app.py" >> app-structure-report.txt
echo "Size: $(ls -lh app.py | awk '{print $5}')" >> app-structure-report.txt
echo "Lines: $(wc -l < app.py)" >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Extract function/class definitions
echo "=== FUNCTION/CLASS DEFINITIONS ===" >> app-structure-report.txt
grep -E "^def |^class " app.py | head -30 >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Extract imports
echo "=== CURRENT IMPORTS ===" >> app-structure-report.txt
grep -E "^import |^from " app.py | head -20 >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Find Streamlit layout structure
echo "=== STREAMLIT LAYOUT STRUCTURE ===" >> app-structure-report.txt
grep -E "st\.sidebar|st\.tabs|st\.columns|st\.container|st\.expander" app.py | head -20 >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Find session state usage
echo "=== SESSION STATE USAGE ===" >> app-structure-report.txt
grep -E "st\.session_state" app.py | head -15 >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Find LLM/chat integration points
echo "=== CHAT/LLM INTEGRATION POINTS ===" >> app-structure-report.txt
grep -E "chat_message|messages|response|anthropic" app.py | head -15 >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Show first 100 lines to see initialization
echo "=== APP INITIALIZATION (First 100 Lines) ===" >> app-structure-report.txt
head -100 app.py >> app-structure-report.txt
echo "" >> app-structure-report.txt

# Show last 50 lines to see main execution
echo "=== APP MAIN EXECUTION (Last 50 Lines) ===" >> app-structure-report.txt
tail -50 app.py >> app-structure-report.txt

cat app-structure-report.txt
