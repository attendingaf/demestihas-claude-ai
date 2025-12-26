
import { supabase, TABLES } from "./src/db.js";

async function checkVantage() {
    console.log("🦅 Checking Vantage Access...");

    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

    console.log("Debug Info:");
    console.log(`- SUPABASE_URL: ${url ? url.substring(0, 15) + '...' : 'UNDEFINED'}`);
    console.log(`- SMB Key found: ${!!key}`);
    console.log(`- Fallback used: ${!process.env.SUPABASE_ANON_KEY && !!process.env.SUPABASE_KEY ? 'Yes' : 'No'}`);

    try {
        const { data: tasks, error } = await supabase
            .from(TABLES.TASKS)
            .select('count', { count: 'exact', head: true });

        if (error) {
            console.error("❌ Supabase Error:", error.message);
            // If it's a fetch error, it might print more details
            if (error.cause) console.error("Cause:", error.cause);
            process.exit(1);
        }

        console.log(`✅ Connection Successful!`);

        // Try to insert a test task to verify write access
        console.log("📝 Attempting write test...");
        const testTask = {
            title: "Vantage Connection Test",
            quadrant: "inbox",
            context: "Automated verification script",
            owner: "Antigravity",
            status: "active"
        };

        const { data: inserted, error: insertError } = await supabase
            .from(TABLES.TASKS)
            .insert(testTask)
            .select()
            .single();

        if (insertError) {
            console.error("❌ Write Error:", insertError.message);
        } else {
            console.log(`✅ Write Successful! Created task ID: ${inserted.id}`);

            // Cleanup
            await supabase.from(TABLES.TASKS).delete().eq('id', inserted.id);
            console.log("🧹 Cleanup complete.");
        }

    } catch (e: any) {
        console.error("❌ Unexpected Error:", e.message);
        if (e.cause) console.error("Cause:", e.cause);
        process.exit(1);
    }
}

checkVantage();
