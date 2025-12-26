import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load environment variables from the root .env or specific locations
// Priority: 
// 1. Process environment (if passed by caller)
// 2. .env in service directory
// 3. .env in project root
// 4. .env in claude-desktop-rag (legacy fallback)

dotenv.config({ path: path.join(__dirname, '../.env') });
dotenv.config({ path: path.join(__dirname, '../../../.env') });
dotenv.config({ path: path.join(__dirname, '../../../claude-desktop-rag/.env') });

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.warn("⚠️ Vantage Service: SUPABASE_URL or SUPABASE_ANON_KEY missing from environment.");
}

export const supabase = createClient(supabaseUrl || 'https://placeholder.supabase.co', supabaseKey || 'placeholder');

export const TABLES = {
    TASKS: 'vantage_tasks',
    CHANGELOG: 'vantage_changelog'
};
