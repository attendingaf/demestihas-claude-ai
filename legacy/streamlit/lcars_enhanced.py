"""
Enhanced LCARS Theme for DemestiChat
Fully immersive Star Trek LCARS interface with animations and status displays
"""

# Enhanced LCARS CSS with authentic Star Trek styling
LCARS_ENHANCED_CSS = """
<style>
/* ============================================================================
   LCARS ENHANCED THEME - STAR TREK TNG INTERFACE
   ============================================================================ */

/* FONTS */
@import url('https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

/* UNIVERSAL FONT ENFORCEMENT */
.stApp, .stApp * {
    font-family: 'Orbitron', 'Antonio', sans-serif !important;
}

/* GLOBAL RESET - PURE BLACK BACKGROUND */
html, body, [class*="css"], .stApp {
    background-color: #000000 !important;
    color: #FF9C00 !important;
}

/* ============================================================================
   LCARS COLOR PALETTE (Authentic TNG Colors)
   ============================================================================ */
:root {
    --lcars-orange: #FF9C00;
    --lcars-peach: #FFCC99;
    --lcars-red: #CC6666;
    --lcars-pink: #CC99CC;
    --lcars-blue: #9999CC;
    --lcars-purple: #CC66CC;
    --lcars-tan: #FFCC99;
    --lcars-yellow: #FFFF00;
    --lcars-black: #000000;
}

/* ============================================================================
   SIDEBAR - THE CLASSIC LCARS ELBOW
   ============================================================================ */
section[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 40px solid var(--lcars-pink) !important;
    border-top-right-radius: 0px !important;
    position: relative;
}

/* LCARS Elbow Cap (Top) */
section[data-testid="stSidebar"]::before {
    content: "";
    position: absolute;
    top: 0;
    right: -40px;
    width: 40px;
    height: 100px;
    background-color: var(--lcars-pink);
    border-top-right-radius: 40px;
}

/* LCARS Elbow Cap (Bottom) */
section[data-testid="stSidebar"]::after {
    content: "";
    position: absolute;
    bottom: 0;
    right: -40px;
    width: 40px;
    height: 100px;
    background-color: var(--lcars-pink);
    border-bottom-right-radius: 40px;
}

/* ============================================================================
   TYPOGRAPHY - UPPERCASE LCARS STYLE
   ============================================================================ */
h1, h2, h3, h4, h5, h6 {
    text-transform: uppercase !important;
    color: var(--lcars-orange) !important;
    letter-spacing: 3px !important;
    font-weight: 900 !important;
    margin-bottom: 1.5rem !important;
}

h1 {
    font-size: 3rem !important;
    border-bottom: 6px solid var(--lcars-pink);
    display: inline-block;
    padding-right: 3rem;
    border-bottom-right-radius: 30px;
    animation: lcars-pulse 2s infinite;
}

@keyframes lcars-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
}

h2 {
    font-size: 2rem !important;
    color: var(--lcars-blue) !important;
}

h3 {
    font-size: 1.5rem !important;
    color: var(--lcars-peach) !important;
}

p, .stMarkdown, li, span, div {
    color: var(--lcars-blue) !important;
    font-size: 1.1rem !important;
    line-height: 1.6 !important;
    letter-spacing: 0.5px !important;
}

/* ============================================================================
   BUTTONS - CLASSIC LCARS PILLS
   ============================================================================ */
div.stButton > button {
    background: linear-gradient(90deg, var(--lcars-orange) 0%, var(--lcars-peach) 100%) !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 25px !important;
    text-transform: uppercase !important;
    font-weight: 900 !important;
    letter-spacing: 2px !important;
    padding: 0.75rem 2.5rem !important;
    margin-bottom: 0.75rem !important;
    width: 100% !important;
    text-align: right !important;
    font-size: 1.1rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(255, 156, 0, 0.4) !important;
    position: relative;
    overflow: hidden;
}

/* Button hover effect */
div.stButton > button:hover {
    background: linear-gradient(90deg, var(--lcars-yellow) 0%, var(--lcars-orange) 100%) !important;
    transform: scaleX(1.05) translateX(5px) !important;
    box-shadow: 0 6px 20px rgba(255, 204, 0, 0.6) !important;
}

/* Button active effect */
div.stButton > button:active {
    transform: scaleX(0.98) !important;
}

/* Button scan line animation */
div.stButton > button::before {
    content: "";
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    animation: lcars-scan 3s infinite;
}

@keyframes lcars-scan {
    0% { left: -100%; }
    100% { left: 100%; }
}

/* Primary button variant */
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, var(--lcars-red) 0%, var(--lcars-pink) 100%) !important;
}

/* Secondary button variant */
div.stButton > button[kind="secondary"] {
    background: linear-gradient(90deg, var(--lcars-blue) 0%, var(--lcars-purple) 100%) !important;
    color: #FFFFFF !important;
}

/* ============================================================================
   INPUTS & TEXT AREAS
   ============================================================================ */
div[data-baseweb="input"], 
div[data-baseweb="textarea"],
.stTextInput > div > div,
.stTextArea > div > div {
    background-color: #000000 !important;
    border: 3px solid var(--lcars-blue) !important;
    border-radius: 20px !important;
    padding: 0.5rem !important;
}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    color: var(--lcars-orange) !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
    background-color: transparent !important;
}

/* Input focus effect */
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: var(--lcars-orange) !important;
    box-shadow: 0 0 20px rgba(255, 156, 0, 0.5) !important;
}

/* ============================================================================
   CHAT MESSAGES - LCARS PANELS
   ============================================================================ */
.stChatMessage {
    background-color: #000000 !important;
    border: 3px solid var(--lcars-pink) !important;
    border-radius: 25px !important;
    border-bottom-right-radius: 0 !important;
    border-top-left-radius: 0 !important;
    padding: 2rem !important;
    margin-bottom: 1.5rem !important;
    position: relative;
    box-shadow: 0 0 30px rgba(204, 153, 204, 0.3) !important;
}

/* User message styling */
.stChatMessage[data-testid="user-message"] {
    border-color: var(--lcars-orange) !important;
    box-shadow: 0 0 30px rgba(255, 156, 0, 0.3) !important;
}

.stChatMessage[data-testid="user-message"] p {
    color: var(--lcars-orange) !important;
}

/* Assistant message styling */
.stChatMessage[data-testid="assistant-message"] {
    border-color: var(--lcars-blue) !important;
    box-shadow: 0 0 30px rgba(153, 153, 204, 0.3) !important;
}

.stChatMessage[data-testid="assistant-message"] p {
    color: var(--lcars-blue) !important;
}

/* LCARS corner decorations */
.stChatMessage::before {
    content: "";
    position: absolute;
    top: -3px;
    left: -3px;
    width: 40px;
    height: 40px;
    border-top: 3px solid var(--lcars-pink);
    border-left: 3px solid var(--lcars-pink);
    border-top-left-radius: 25px;
}

.stChatMessage::after {
    content: "";
    position: absolute;
    bottom: -3px;
    right: -3px;
    width: 40px;
    height: 40px;
    border-bottom: 3px solid var(--lcars-pink);
    border-right: 3px solid var(--lcars-pink);
}

/* ============================================================================
   CHAT INPUT - COMMAND LINE STYLE
   ============================================================================ */
.stChatInputContainer {
    padding-bottom: 1.5rem !important;
}

.stChatInputContainer > div {
    background-color: #000000 !important;
    border: 4px solid var(--lcars-orange) !important;
    border-radius: 25px !important;
    box-shadow: 0 0 40px rgba(255, 156, 0, 0.5) !important;
}

.stChatInputContainer input {
    color: var(--lcars-orange) !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* ============================================================================
   EXPANDERS - COLLAPSIBLE PANELS
   ============================================================================ */
.streamlit-expanderHeader {
    background-color: #000000 !important;
    border: 2px solid var(--lcars-orange) !important;
    border-radius: 20px !important;
    color: var(--lcars-orange) !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    padding: 1rem 1.5rem !important;
}

.streamlit-expanderHeader:hover {
    background-color: var(--lcars-orange) !important;
    color: #000000 !important;
    box-shadow: 0 0 20px rgba(255, 156, 0, 0.6) !important;
}

div[data-testid="stExpander"] {
    border: none !important;
    background-color: transparent !important;
}

/* ============================================================================
   CODE BLOCKS - TERMINAL STYLE
   ============================================================================ */
code {
    background-color: #1a1a1a !important;
    color: var(--lcars-orange) !important;
    border: 1px solid var(--lcars-blue) !important;
    border-radius: 8px !important;
    padding: 0.3em 0.6em !important;
    font-family: 'Courier New', monospace !important;
}

pre {
    background-color: #0a0a0a !important;
    border: 2px solid var(--lcars-blue) !important;
    border-radius: 15px !important;
    padding: 1.5rem !important;
}

/* ============================================================================
   DIVIDERS - LCARS BARS
   ============================================================================ */
hr {
    border: none !important;
    height: 4px !important;
    background: linear-gradient(90deg, var(--lcars-orange) 0%, var(--lcars-pink) 50%, var(--lcars-blue) 100%) !important;
    margin: 2rem 0 !important;
    border-radius: 2px !important;
}

/* ============================================================================
   RADIO BUTTONS - LCARS STYLE
   ============================================================================ */
div[role="radiogroup"] label {
    background-color: transparent !important;
    color: var(--lcars-blue) !important;
    padding: 0.5rem 1rem !important;
    border-radius: 15px !important;
    transition: all 0.2s !important;
}

div[role="radiogroup"] label:hover {
    background-color: rgba(153, 153, 204, 0.1) !important;
}

div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
    background-color: #000000 !important;
    border: 2px solid var(--lcars-blue) !important;
}

div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child[aria-checked="true"] {
    background-color: var(--lcars-orange) !important;
    border-color: var(--lcars-orange) !important;
    box-shadow: 0 0 15px rgba(255, 156, 0, 0.6) !important;
}

/* ============================================================================
   SCROLLBAR - LCARS STYLE
   ============================================================================ */
::-webkit-scrollbar {
    width: 20px;
    background-color: #000000;
}

::-webkit-scrollbar-track {
    background-color: #1a1a1a;
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--lcars-orange) 0%, var(--lcars-pink) 100%);
    border-radius: 10px;
    border: 2px solid #000000;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--lcars-yellow) 0%, var(--lcars-orange) 100%);
}

/* ============================================================================
   CAPTIONS & LABELS
   ============================================================================ */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--lcars-peach) !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    font-size: 0.9rem !important;
}

/* ============================================================================
   LOADING SPINNER - LCARS ANIMATION
   ============================================================================ */
.stSpinner > div {
    border-color: var(--lcars-orange) !important;
    border-top-color: transparent !important;
}

/* ============================================================================
   SUCCESS/ERROR/WARNING MESSAGES
   ============================================================================ */
.stSuccess {
    background-color: rgba(153, 204, 153, 0.1) !important;
    border-left: 4px solid #99CC99 !important;
    color: #99CC99 !important;
}

.stError {
    background-color: rgba(204, 102, 102, 0.1) !important;
    border-left: 4px solid var(--lcars-red) !important;
    color: var(--lcars-red) !important;
}

.stWarning {
    background-color: rgba(255, 204, 0, 0.1) !important;
    border-left: 4px solid var(--lcars-yellow) !important;
    color: var(--lcars-yellow) !important;
}

.stInfo {
    background-color: rgba(153, 153, 204, 0.1) !important;
    border-left: 4px solid var(--lcars-blue) !important;
    color: var(--lcars-blue) !important;
}

/* ============================================================================
   FILE UPLOADER
   ============================================================================ */
[data-testid="stFileUploader"] {
    background-color: #000000 !important;
    border: 2px dashed var(--lcars-blue) !important;
    border-radius: 20px !important;
    padding: 2rem !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--lcars-orange) !important;
    background-color: rgba(255, 156, 0, 0.05) !important;
}

/* ============================================================================
   PROGRESS BARS - LCARS STYLE
   ============================================================================ */
.stProgress > div > div {
    background-color: var(--lcars-orange) !important;
    border-radius: 10px !important;
}

.stProgress > div {
    background-color: #1a1a1a !important;
    border-radius: 10px !important;
}

/* ============================================================================
   SELECTBOX & MULTISELECT
   ============================================================================ */
div[data-baseweb="select"] {
    background-color: #000000 !important;
    border: 2px solid var(--lcars-blue) !important;
    border-radius: 15px !important;
}

div[data-baseweb="select"]:hover {
    border-color: var(--lcars-orange) !important;
}

/* ============================================================================
   TABS - LCARS PANELS
   ============================================================================ */
button[data-baseweb="tab"] {
    background-color: #000000 !important;
    border: 2px solid var(--lcars-blue) !important;
    border-radius: 15px 15px 0 0 !important;
    color: var(--lcars-blue) !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background-color: var(--lcars-orange) !important;
    border-color: var(--lcars-orange) !important;
    color: #000000 !important;
}

/* ============================================================================
   ANIMATIONS
   ============================================================================ */
@keyframes lcars-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

@keyframes lcars-slide-in {
    from {
        transform: translateX(-100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Apply slide-in animation to chat messages */
.stChatMessage {
    animation: lcars-slide-in 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

</style>
"""


# LCARS Header Component (HTML/CSS/JS for animated header)
LCARS_HEADER_HTML = """
<div class="lcars-header">
    <div class="lcars-time-display">
        <div class="lcars-date" id="lcars-date">FRIDAY • 22. 03. 2019</div>
        <div class="lcars-time" id="lcars-time">12:24:59</div>
    </div>
    <div class="lcars-title">MASTER SITUATION DISPLAY</div>
    <div class="lcars-status-indicators">
        <div class="lcars-indicator active">ONLINE</div>
        <div class="lcars-indicator">SYSTEMS NOMINAL</div>
    </div>
</div>

<style>
.lcars-header {
    background-color: #000000;
    padding: 1.5rem 2rem;
    border-bottom: 4px solid #CC99CC;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.lcars-time-display {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.lcars-date {
    color: #CC99CC;
    font-size: 0.9rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.lcars-time {
    color: #FF9C00;
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: 3px;
    font-family: 'Orbitron', sans-serif;
}

.lcars-title {
    color: #FF9C00;
    font-size: 2rem;
    font-weight: 900;
    letter-spacing: 4px;
    text-transform: uppercase;
}

.lcars-status-indicators {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-end;
}

.lcars-indicator {
    background-color: #CC6666;
    color: #000000;
    padding: 0.5rem 1.5rem;
    border-radius: 20px;
    font-weight: 700;
    letter-spacing: 1px;
    font-size: 0.9rem;
}

.lcars-indicator.active {
    background-color: #99CC99;
    animation: lcars-blink 2s infinite;
}

@keyframes lcars-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
</style>

<script>
function updateLCARSTime() {
    const now = new Date();
    
    // Update time
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('lcars-time').textContent = `${hours}:${minutes}:${seconds}`;
    
    // Update date
    const days = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
    const day = days[now.getDay()];
    const date = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    document.getElementById('lcars-date').textContent = `${day} • ${date}. ${month}. ${year}`;
}

// Update time every second
setInterval(updateLCARSTime, 1000);
updateLCARSTime(); // Initial call
</script>
"""
