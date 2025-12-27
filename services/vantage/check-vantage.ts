
import { supabase, TABLES } from "./src/db.js";

async function checkVantage() {
    console.log("🦅 Checking Vantage Connectivity...");

    const url = process.env.SUPABASE_URL || '';

    console.log(`URL Check: ${url.startsWith('https://') ? 'HTTPS OK' : '⚠️ Not HTTPS'}`);
    console.log(`Domain Check: ${url.includes('.supabase.co') ? 'Supabase.co OK' : '⚠️ Weird Domain'}`);

    // Try raw fetch
    try {
        console.log("Attempting raw fetch to REST endpoint...");
        const restUrl = `${url}/rest/v1/`;
        const res = await fetch(restUrl, {
            headers: {
                'apikey': process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY || ''
            }
        });
        console.log(`Raw Fetch Result: ${res.status} ${res.statusText}`);
    } catch (e: any) {
        console.error(`❌ Raw Fetch Failed: ${e.message}`);
        if (e.cause) console.error("Cause:", e.cause);
    }

    // Then Supabase Client
    try {
        const { data: tasks, error } = await supabase
            .from(TABLES.TASKS)
            .select('count', { count: 'exact', head: true });

        if (error) {
            console.error("❌ Supabase Client Error:", error.message);
        } else {
            console.log(`✅ Supabase Client Connected!`);
        }
    } catch (e: any) {
        console.error("❌ DB Check Error:", e.message);
    }
}

checkVantage();
