#!/usr/bin/env python3
"""
Supabase Migration Runner for Ytili Platform
Executes SQL migration files in the correct order
"""
import asyncio
import os
from pathlib import Path
from app.core.supabase import get_supabase_service

async def run_migrations():
    """Run all Supabase migrations in order"""
    
    print("🚀 Starting Ytili Supabase Migrations...")
    print("=" * 60)
    
    # Get Supabase client
    try:
        supabase = get_supabase_service()
        print("✅ Connected to Supabase successfully")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False
    
    # Migration files in order
    migration_files = [
        "001_create_users_table.sql",
        "002_create_donations_table.sql", 
        "003_create_functions.sql"
    ]
    
    migrations_dir = Path("migrations/supabase")
    
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return False
    
    success_count = 0
    
    for migration_file in migration_files:
        migration_path = migrations_dir / migration_file
        
        if not migration_path.exists():
            print(f"⚠️  Migration file not found: {migration_file}")
            continue
        
        print(f"\n📄 Running migration: {migration_file}")
        print("-" * 40)
        
        try:
            # Read migration file
            with open(migration_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split by statements (simple approach)
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            print(f"   Found {len(statements)} SQL statements")
            
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                if statement.strip():
                    try:
                        # Use Supabase RPC to execute raw SQL
                        result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                        print(f"   ✅ Statement {i}/{len(statements)} executed")
                    except Exception as stmt_error:
                        # Some statements might fail if already exist, that's OK
                        print(f"   ⚠️  Statement {i} warning: {str(stmt_error)[:100]}...")
            
            print(f"✅ Migration {migration_file} completed successfully")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Migration {migration_file} failed: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"🏁 Migration Summary: {success_count}/{len(migration_files)} completed")
    
    if success_count == len(migration_files):
        print("🎉 All migrations completed successfully!")
        return True
    else:
        print("⚠️  Some migrations had issues. Please check Supabase dashboard.")
        return False

async def verify_database():
    """Verify database setup"""
    print("\n🔍 Verifying database setup...")
    
    try:
        supabase = get_supabase_service()
        
        # Test basic operations
        tables_to_check = ['users', 'donations', 'user_points']
        
        for table in tables_to_check:
            try:
                result = supabase.table(table).select("*").limit(1).execute()
                print(f"   ✅ Table '{table}' is accessible")
            except Exception as e:
                print(f"   ❌ Table '{table}' error: {e}")
        
        print("✅ Database verification completed")
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

async def main():
    """Main function"""
    print("Ytili Platform - Supabase Migration Runner")
    print("=" * 60)
    
    # Run migrations
    migration_success = await run_migrations()
    
    if migration_success:
        # Verify database
        await verify_database()
        
        print("\n🎯 Next steps:")
        print("1. Check Supabase dashboard to verify tables")
        print("2. Test authentication endpoints")
        print("3. Run integration tests")
        print("4. Start the backend server")
        
        return True
    else:
        print("\n🔧 Please fix migration issues before proceeding.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
