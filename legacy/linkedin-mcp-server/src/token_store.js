const fs = require('fs');
const path = require('path');

const TOKEN_FILE = path.join(__dirname, '../tokens.json');

function saveToken(tokenData) {
    fs.writeFileSync(TOKEN_FILE, JSON.stringify(tokenData, null, 2));
}

function loadToken() {
    if (fs.existsSync(TOKEN_FILE)) {
        try {
            return JSON.parse(fs.readFileSync(TOKEN_FILE, 'utf8'));
        } catch (e) {
            console.error("Error reading token file:", e);
            return null;
        }
    }
    return null;
}

module.exports = { saveToken, loadToken };
