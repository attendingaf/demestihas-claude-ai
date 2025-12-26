"""
LCARS Theme for Streamlit - Production Quality
Based on research from louh/lcars, TheLCARS.com, and authentic TNG design
"""

NEO_PROFESSIONAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp { background-color: #0A0A0A !important; font-family: 'Inter', sans-serif !important; }
section[data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #333 !important; }
h1, h2, h3 { color: #FFFFFF !important; }
p, div, span { color: #A1A1AA !important; }
div.stButton > button { background-color: #262626 !important; color: #FFFFFF !important; border: 1px solid #404040 !important; border-radius: 6px !important; }
.stChatMessage { background-color: #171717 !important; border: 1px solid #262626 !important; border-radius: 8px !important; }
</style>
"""

LCARS_CSS = """
<style>
/* ============================================================================
   LCARS THEME - AUTHENTIC STAR TREK TNG
   Based on production implementations and authentic design patterns
   ============================================================================ */

/* FONTS - Antonio for headers, system fonts for body */
@import url('https://fonts.googleapis.com/css2?family=Antonio:wght@700&display=swap');

/* ===== GLOBAL RESET ===== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body {
    background-color: #000000 !important;
    color: #FFCC99 !important;
}

.stApp {
    background-color: #000000 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }

/* ===== SIDEBAR - CLASSIC LCARS ELBOW ===== */
section[data-testid="stSidebar"] {
    background: linear-gradient(to right, 
        #000000 0%, 
        #000000 calc(100% - 50px), 
        #CC99CC calc(100% - 50px), 
        #CC99CC 100%) !important;
    border-right: none !important;
}

section[data-testid="stSidebar"] > div:first-child {
    padding-right: 60px !important;
}

/* Sidebar elbow caps */
section[data-testid="stSidebar"]::before {
    content: "";
    position: fixed;
    top: 0;
    right: 0;
    width: 50px;
    height: 120px;
    background-color: #CC99CC;
    border-top-right-radius: 50px;
    z-index: 999;
}

section[data-testid="stSidebar"]::after {
    content: "";
    position: fixed;
    bottom: 0;
    right: 0;
    width: 50px;
    height: 120px;
    background-color: #CC99CC;
    border-bottom-right-radius: 50px;
    z-index: 999;
}

/* ===== TYPOGRAPHY ===== */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Antonio', sans-serif !important;
    text-transform: uppercase !important;
    color: #FF9966 !important;
    letter-spacing: 6px !important;
    font-weight: 700 !important;
    margin: 1.5rem 0 !important;
}

h1 {
    font-size: 2.5rem !important;
    color: #FF9966 !important;
    text-shadow: 0 0 20px rgba(255, 153, 102, 0.5);
    margin: 1rem 0 !important;
}

h2 {
    font-size: 2rem !important;
    color: #FFCC99 !important;
    margin: 1rem 0 !important;
}

h3 {
    font-size: 1.5rem !important;
    color: #CC99CC !important;
    margin: 0.8rem 0 !important;
}

p, div, span, li {
    color: #FFCC99 !important;
    font-size: 1.15rem !important;
    line-height: 1.8 !important;
    letter-spacing: 0.5px !important;
}

/* ===== BUTTONS - AUTHENTIC LCARS PILLS ===== */
div.stButton > button {
    background: linear-gradient(135deg, #FF9966 0%, #FFCC99 100%) !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 30px !important;
    text-transform: uppercase !important;
    font-family: 'Antonio', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 2px !important;
    padding: 0.8rem 2rem !important;
    width: 100% !important;
    text-align: right !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 4px 0 #CC7744, 0 6px 15px rgba(255, 153, 102, 0.4) !important;
    position: relative !important;
}

div.stButton > button:hover {
    background: linear-gradient(135deg, #FFBB88 0%, #FFDDBB 100%) !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 9px 0 #CC7744, 0 12px 30px rgba(255, 153, 102, 0.6) !important;
}

div.stButton > button:active {
    transform: translateY(3px) !important;
    box-shadow: 0 3px 0 #CC7744, 0 4px 10px rgba(255, 153, 102, 0.3) !important;
}

/* Primary button variant */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #CC99CC 0%, #DDAADD 100%) !important;
    box-shadow: 0 6px 0 #996699, 0 8px 20px rgba(204, 153, 204, 0.4) !important;
}

div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #DDAADD 0%, #EEBBEE 100%) !important;
    box-shadow: 0 9px 0 #996699, 0 12px 30px rgba(204, 153, 204, 0.6) !important;
}

/* Secondary button variant */
div.stButton > button[kind="secondary"] {
    background: linear-gradient(135deg, #9999CC 0%, #BBBBEE 100%) !important;
    box-shadow: 0 6px 0 #666699, 0 8px 20px rgba(153, 153, 204, 0.4) !important;
}

/* ===== CHAT MESSAGES - LCARS PANELS ===== */
.stChatMessage {
    background-color: #0a0a0a !important;
    border: 3px solid #FF9966 !important;
    border-radius: 20px !important;
    padding: 1.5rem !important;
    margin: 1rem 0 !important;
    position: relative !important;
    box-shadow: 0 0 20px rgba(255, 153, 102, 0.2), inset 0 0 20px rgba(255, 153, 102, 0.05) !important;
}

/* User messages */
.stChatMessage[data-testid="user-message"] {
    border-color: #FFCC99 !important;
    background: linear-gradient(135deg, #1a0f00 0%, #0a0a0a 100%) !important;
    box-shadow: 0 0 30px rgba(255, 204, 153, 0.2), inset 0 0 30px rgba(255, 204, 153, 0.05) !important;
}

.stChatMessage[data-testid="user-message"] p {
    color: #FFCC99 !important;
}

/* Assistant messages */
.stChatMessage[data-testid="assistant-message"] {
    border-color: #CC99CC !important;
    background: linear-gradient(135deg, #1a0a1a 0%, #0a0a0a 100%) !important;
    box-shadow: 0 0 30px rgba(204, 153, 204, 0.2), inset 0 0 30px rgba(204, 153, 204, 0.05) !important;
}

.stChatMessage[data-testid="assistant-message"] p {
    color: #CC99CC !important;
}

/* LCARS corner accent */
.stChatMessage::before {
    content: "";
    position: absolute;
    top: -4px;
    left: -4px;
    width: 60px;
    height: 60px;
    border-top: 4px solid currentColor;
    border-left: 4px solid currentColor;
    border-top-left-radius: 30px;
}

/* ===== CHAT INPUT - COMMAND LINE ===== */
.stChatInputContainer {
    background-color: #000000 !important;
    padding: 2rem 0 !important;
    border-top: 3px solid #FF9966 !important;
}

.stChatInputContainer > div {
    background: linear-gradient(135deg, #1a0f00 0%, #0a0a0a 100%) !important;
    border: 4px solid #FF9966 !important;
    border-radius: 30px !important;
    box-shadow: 0 0 40px rgba(255, 153, 102, 0.3), inset 0 0 20px rgba(255, 153, 102, 0.1) !important;
}

.stChatInputContainer input {
    color: #FF9966 !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    padding: 1rem !important;
}

.stChatInputContainer input::placeholder {
    color: #CC7744 !important;
    opacity: 0.6 !important;
}

/* ===== TEXT INPUTS ===== */
div[data-baseweb="input"],
div[data-baseweb="textarea"],
.stTextInput > div > div,
.stTextArea > div > div {
    background-color: #0a0a0a !important;
    border: 3px solid #9999CC !important;
    border-radius: 20px !important;
    padding: 0.8rem !important;
}

input, textarea {
    color: #FFCC99 !important;
    font-size: 1.15rem !important;
    letter-spacing: 1px !important;
}

div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: #FF9966 !important;
    box-shadow: 0 0 20px rgba(255, 153, 102, 0.4) !important;
}

/* ===== EXPANDERS - COLLAPSIBLE PANELS ===== */
.streamlit-expanderHeader {
    background: linear-gradient(90deg, #1a0a1a 0%, #0a0a0a 100%) !important;
    border: 3px solid #CC99CC !important;
    border-radius: 25px !important;
    color: #FF9966 !important;
    text-transform: uppercase !important;
    font-family: 'Antonio', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 3px !important;
    padding: 1.2rem 2rem !important;
    font-size: 1.1rem !important;
}

.streamlit-expanderHeader:hover {
    background: linear-gradient(90deg, #CC99CC 0%, #996699 100%) !important;
    color: #000000 !important;
    box-shadow: 0 0 25px rgba(204, 153, 204, 0.5) !important;
}

div[data-testid="stExpander"] {
    border: none !important;
    background-color: transparent !important;
}

/* ===== CAPTIONS & LABELS ===== */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #FF9966 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
}

/* ===== DIVIDERS - LCARS BARS ===== */
hr {
    border: none !important;
    height: 5px !important;
    background: linear-gradient(90deg, 
        #FF9966 0%, 
        #FFCC99 25%, 
        #CC99CC 50%, 
        #9999CC 75%, 
        #FF9966 100%) !important;
    margin: 3rem 0 !important;
    border-radius: 3px !important;
    box-shadow: 0 0 15px rgba(255, 153, 102, 0.5) !important;
}

/* ===== SCROLLBAR - LCARS STYLE ===== */
::-webkit-scrollbar {
    width: 24px;
    background-color: #000000;
}

::-webkit-scrollbar-track {
    background: linear-gradient(90deg, #0a0a0a 0%, #1a1a1a 100%);
    border-radius: 12px;
    margin: 10px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #FF9966 0%, #CC99CC 50%, #9999CC 100%);
    border-radius: 12px;
    border: 4px solid #000000;
    box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.2);
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #FFBB88 0%, #DDAADD 50%, #BBBBEE 100%);
    box-shadow: inset 0 0 15px rgba(255, 255, 255, 0.3), 0 0 20px rgba(255, 153, 102, 0.5);
}

/* ===== ALERTS & MESSAGES ===== */
.stSuccess {
    background: linear-gradient(135deg, rgba(153, 204, 102, 0.15) 0%, rgba(102, 153, 51, 0.05) 100%) !important;
    border-left: 6px solid #99CC66 !important;
    border-radius: 15px !important;
    color: #99CC66 !important;
    padding: 1.5rem !important;
    font-weight: 600 !important;
}

.stError {
    background: linear-gradient(135deg, rgba(204, 102, 102, 0.15) 0%, rgba(153, 51, 51, 0.05) 100%) !important;
    border-left: 6px solid #CC6666 !important;
    border-radius: 15px !important;
    color: #CC6666 !important;
    padding: 1.5rem !important;
    font-weight: 600 !important;
}

.stWarning {
    background: linear-gradient(135deg, rgba(255, 204, 0, 0.15) 0%, rgba(204, 153, 0, 0.05) 100%) !important;
    border-left: 6px solid #FFCC00 !important;
    border-radius: 15px !important;
    color: #FFCC00 !important;
    padding: 1.5rem !important;
    font-weight: 600 !important;
}

.stInfo {
    background: linear-gradient(135deg, rgba(153, 153, 204, 0.15) 0%, rgba(102, 102, 153, 0.05) 100%) !important;
    border-left: 6px solid #9999CC !important;
    border-radius: 15px !important;
    color: #9999CC !important;
    padding: 1.5rem !important;
    font-weight: 600 !important;
}

/* ===== RADIO BUTTONS ===== */
div[role="radiogroup"] label {
    color: #FFCC99 !important;
    font-size: 1.1rem !important;
    padding: 0.8rem 1.5rem !important;
    border-radius: 20px !important;
    transition: all 0.2s !important;
}

div[role="radiogroup"] label:hover {
    background-color: rgba(255, 153, 102, 0.1) !important;
}

div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
    background-color: #0a0a0a !important;
    border: 3px solid #FF9966 !important;
    width: 24px !important;
    height: 24px !important;
}

div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child[aria-checked="true"] {
    background-color: #FF9966 !important;
    border-color: #FF9966 !important;
    box-shadow: 0 0 20px rgba(255, 153, 102, 0.6), inset 0 0 10px rgba(255, 255, 255, 0.3) !important;
}

/* ===== FILE UPLOADER ===== */
[data-testid="stFileUploader"] {
    background: linear-gradient(135deg, #1a0a1a 0%, #0a0a0a 100%) !important;
    border: 4px dashed #CC99CC !important;
    border-radius: 25px !important;
    padding: 3rem !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: #FF9966 !important;
    background: linear-gradient(135deg, #1a0f00 0%, #0a0a0a 100%) !important;
    box-shadow: 0 0 30px rgba(255, 153, 102, 0.2) !important;
}

/* ===== PROGRESS BARS ===== */
.stProgress > div > div {
    background: linear-gradient(90deg, #FF9966 0%, #FFCC99 100%) !important;
    border-radius: 15px !important;
    box-shadow: 0 0 15px rgba(255, 153, 102, 0.5) !important;
}

.stProgress > div {
    background-color: #1a1a1a !important;
    border-radius: 15px !important;
    border: 2px solid #FF9966 !important;
}

/* ===== SELECTBOX & MULTISELECT ===== */
div[data-baseweb="select"] {
    background-color: #0a0a0a !important;
    border: 3px solid #9999CC !important;
    border-radius: 20px !important;
}

div[data-baseweb="select"]:hover {
    border-color: #FF9966 !important;
    box-shadow: 0 0 20px rgba(255, 153, 102, 0.3) !important;
}

/* ===== ANIMATIONS ===== */
@keyframes lcars-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

@keyframes lcars-glow {
    0%, 100% { box-shadow: 0 0 20px rgba(255, 153, 102, 0.3); }
    50% { box-shadow: 0 0 40px rgba(255, 153, 102, 0.6); }
}

@keyframes lcars-slide-in {
    from {
        transform: translateX(-30px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Apply animations */
.stChatMessage {
    animation: lcars-slide-in 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

h1 {
    animation: lcars-glow 3s infinite;
}
</style>
"""

LCARS_HEADER_HTML = """
<div style="background: linear-gradient(135deg, #0a0a0a 0%, #000000 100%); padding: 1.5rem 2rem; margin-bottom: 2rem; border-bottom: 4px solid #FF9966; box-shadow: 0 6px 20px rgba(255, 153, 102, 0.3);">
    <div style="display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 1rem; align-items: center;">
        <!-- Left: Time Display -->
        <div>
            <div style="color: #CC99CC; font-size: 0.9rem; letter-spacing: 2px; margin-bottom: 0.5rem; font-weight: 700;" id="lcars-date">
                LOADING...
            </div>
            <div style="color: #FF9966; font-size: 3rem; font-weight: 900; font-family: 'Antonio', sans-serif; letter-spacing: 4px; text-shadow: 0 0 20px rgba(255, 153, 102, 0.6);" id="lcars-time">
                --:--:--
            </div>
        </div>
        
        <!-- Center: Title -->
        <div style="text-align: center;">
            <div style="color: #FF9966; font-size: 2.5rem; font-weight: 900; font-family: 'Antonio', sans-serif; letter-spacing: 6px; text-shadow: 0 0 30px rgba(255, 153, 102, 0.5);">
                DEMESTICHAT
            </div>
            <div style="color: #FFCC99; font-size: 1rem; letter-spacing: 3px; margin-top: 0.5rem; font-weight: 600;">
                MASTER SITUATION DISPLAY
            </div>
        </div>
        
        <!-- Right: Status Indicators -->
        <div style="text-align: right; display: flex; flex-direction: column; gap: 0.8rem;">
            <div style="background: linear-gradient(135deg, #99CC66 0%, #77AA44 100%); color: #000; padding: 0.6rem 1.5rem; border-radius: 20px; font-weight: 700; font-size: 0.9rem; letter-spacing: 1px; box-shadow: 0 3px 0 #558833, 0 4px 15px rgba(153, 204, 102, 0.4); animation: lcars-pulse 2s infinite;">
                ONLINE
            </div>
            <div style="background: linear-gradient(135deg, #CC99CC 0%, #AA77AA 100%); color: #000; padding: 0.6rem 1.5rem; border-radius: 20px; font-weight: 700; font-size: 0.9rem; letter-spacing: 1px; box-shadow: 0 3px 0 #885588, 0 4px 15px rgba(204, 153, 204, 0.4);">
                SYSTEMS NOMINAL
            </div>
        </div>
    </div>
</div>

<style>
@keyframes lcars-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.85; transform: scale(0.98); }
}
</style>

<script>
function updateLCARSTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('lcars-time').textContent = hours + ':' + minutes + ':' + seconds;
    
    const days = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
    const day = days[now.getDay()];
    const date = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    document.getElementById('lcars-date').textContent = day + ' • ' + date + '.' + month + '.' + year;
}
setInterval(updateLCARSTime, 1000);
updateLCARSTime();
</script>
"""

LCARS_ENHANCED_CSS = LCARS_CSS
