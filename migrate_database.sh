#!/bin/bash

# Database Migration Script - Monolithic to Microservices
# This script copies data from your monolithic database to microservices database

echo "🔄 Migrating database from monolithic app to microservices..."
echo ""

# Get the monolithic database path
MONOLITH_DB="../telehealth.db"
MICROSERVICES_CONTAINER="telehealth-postgres"
POSTGRES_USER="telehealth_user"
POSTGRES_DB="telehealth"

# Check if monolithic database exists
if [ ! -f "$MONOLITH_DB" ]; then
    echo "❌ Monolithic database not found at $MONOLITH_DB"
    echo "Please specify the correct path to your SQLite database"
    exit 1
fi

echo "✓ Found monolithic database: $MONOLITH_DB"
echo ""

# Option 1: If using SQLite in monolith
echo "📊 Your monolithic app uses SQLite"
echo "Choose migration method:"
echo "  1. Export from SQLite and import to PostgreSQL (recommended)"
echo "  2. Point microservices to same SQLite database (temporary)"
echo ""

read -p "Enter choice (1 or 2): " choice

if [ "$choice" == "1" ]; then
    echo ""
    echo "🔧 Export/Import Migration Steps:"
    echo ""
    echo "1️⃣ Export users from monolithic database:"
    echo "   sqlite3 $MONOLITH_DB 'SELECT * FROM users;' > users_export.csv"
    echo ""
    echo "2️⃣ Import to microservices (run from this directory):"
    echo '   docker-compose exec -T postgres psql -U telehealth_user -d telehealth -c "\\COPY users FROM '/tmp/users_export.csv' WITH CSV HEADER"'
    echo ""
    echo "3️⃣ Repeat for each table: appointments, doctor_availability, vitals, etc."
    echo ""
    
elif [ "$choice" == "2" ]; then
    echo ""
    echo "🔧 Quick SQLite Migration:"
    echo ""
    echo "1️⃣ Update docker-compose.yml to mount your SQLite database"
    echo "2️⃣ Update .env to point to SQLite:"
    echo "   DATABASE_URL=sqlite:///../telehealth.db"
    echo "3️⃣ Restart services: docker-compose restart"
    echo ""
    echo "⚠️ Note: This is temporary. SQLite doesn't support concurrent connections well."
    echo ""
fi

echo ""
echo "📝 Alternative: Fresh Start (Recommended for Testing)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Your microservices have a fresh PostgreSQL database."
echo "You can:"
echo "  • Register new test users via the API"
echo "  • Use the frontend registration page"
echo "  • Let the microservices create fresh data"
echo ""
echo "This is ideal for testing the new architecture!"
echo ""

echo "✅ Migration guide complete!"
echo "Choose the approach that best fits your needs."
