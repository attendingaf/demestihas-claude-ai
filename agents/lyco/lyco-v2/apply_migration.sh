#!/bin/bash
# Apply Rounds Mode migration to Supabase

# Supabase connection details
SUPABASE_HOST="db.oletgdpevhdxbywrqeyh.supabase.co"
SUPABASE_DB="postgres"
SUPABASE_USER="postgres"

echo "Applying Rounds Mode migration to Supabase..."
echo "You'll be prompted for the database password."
echo ""
echo "To get your password:"
echo "1. Go to: https://supabase.com/dashboard/project/oletgdpevhdxbywrqeyh/settings/database"
echo "2. Find 'Database Password' and click 'Reveal'"
echo "3. Copy and paste it when prompted below"
echo ""

# Apply the migration
psql -h $SUPABASE_HOST -p 5432 -d $SUPABASE_DB -U $SUPABASE_USER < migrations/rounds_mode.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration applied successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Restart Lyco server: ./deploy_local.sh"
    echo "2. Test Rounds Mode: open http://localhost:8000/rounds"
else
    echo ""
    echo "❌ Migration failed. Please check your password and try again."
fi
