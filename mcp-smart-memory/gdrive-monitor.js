import { google } from 'googleapis';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import axios from 'axios';
import fs from 'fs/promises';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

class GDriveMonitor {
  constructor() {
    this.drive = null;
    this.auth = null;
    this.lastCheck = null;
    this.monitoredFolders = {
      'Meeting Notes': '1914m3M7kRzkd5RJqAfzRY9EBcJrKemZC',
      'Project Documentation': null, // Find and add folder ID
      'OXOS Medical': null, // Find and add folder ID
      'Consulting': null // Find and add folder ID
    };
  }

  async initialize() {
    // OAuth2 setup using existing Gmail credentials
    const auth = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      process.env.GOOGLE_REDIRECT_URI
    );

    // Load token from stored credentials
    const tokenPath = path.join(__dirname, '../google_credentials/token.json');
    const token = JSON.parse(await fs.readFile(tokenPath, 'utf8'));
    auth.setCredentials(token);

    this.auth = auth;
    this.drive = google.drive({ version: 'v3', auth });
  }

  async checkForNewFiles() {
    const now = new Date();
    const checkTime = this.lastCheck || new Date(Date.now() - 60 * 60 * 1000); // Last hour if first run

    for (const [folderName, folderId] of Object.entries(this.monitoredFolders)) {
      if (!folderId) continue;

      try {
        // Query for new/modified files
        const response = await this.drive.files.list({
          q: `'${folderId}' in parents and modifiedTime > '${checkTime.toISOString()}'`,
          fields: 'files(id, name, mimeType, modifiedTime, size)',
          orderBy: 'modifiedTime desc'
        });

        for (const file of response.data.files) {
          await this.processFile(file, folderName);
        }
      } catch (error) {
        console.error(`Error checking folder ${folderName}:`, error);
      }
    }

    this.lastCheck = now;
  }

  async processFile(file, folderName) {
    console.log(`Processing: ${file.name} from ${folderName}`);

    // Only process Google Docs and text files
    if (!file.mimeType.includes('document') && !file.mimeType.includes('text')) {
      return;
    }

    try {
      // Export as plain text
      const response = await this.drive.files.export({
        fileId: file.id,
        mimeType: 'text/plain'
      });

      // Send to memory API for processing
      await axios.post('http://localhost:7777/ingest/document', {
        fileId: file.id,
        fileName: file.name,
        folder: folderName,
        content: response.data,
        mimeType: file.mimeType,
        modifiedTime: file.modifiedTime
      });

      console.log(`✅ Ingested: ${file.name}`);
    } catch (error) {
      console.error(`Failed to process ${file.name}:`, error);
    }
  }

  async startMonitoring(intervalMinutes = 5) {
    await this.initialize();

    // Initial check
    await this.checkForNewFiles();

    // Set up interval
    setInterval(async () => {
      await this.checkForNewFiles();
    }, intervalMinutes * 60 * 1000);

    console.log(`📂 Monitoring Google Drive every ${intervalMinutes} minutes`);
  }
}

// Start monitoring if run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const monitor = new GDriveMonitor();
  monitor.startMonitoring();
}

export default GDriveMonitor;
