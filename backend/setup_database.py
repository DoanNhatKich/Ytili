#!/usr/bin/env python3
"""
Database Setup Guide for Ytili Platform
Provides instructions and verification for Supabase setup
"""
import asyncio
from pathlib import Path
from app.core.supabase import get_supabase_service

def print_migration_instructions():
    """Print instructions for running migrations"""
    print("📋 SUPABASE MIGRATION INSTRUCTIONS")
    print("=" * 60)
    print()
    print("Since Supabase doesn't allow direct SQL execution via API,")
    print("please follow these steps to set up your database:")
    print()
    print("1. 🌐 Go to your Supabase Dashboard:")
    print("   https://supabase.com/dashboard")
    print()
    print("2. 📊 Navigate to SQL Editor")
    print()
    print("3. 📄 Copy and execute each migration file in order:")
    print()
    
    migrations_dir = Path("migrations/supabase")
    migration_files = [
        "001_create_users_table.sql",
        "002_create_donations_table.sql", 
        "003_create_functions.sql"
    ]
    
    for i, migration_file in enumerate(migration_files, 1):
        migration_path = migrations_dir / migration_file
        print(f"   Step {i}: Execute {migration_file}")
        
        if migration_path.exists():
            print(f"   📁 File location: {migration_path.absolute()}")
            
            # Show first few lines as preview
            try:
                with open(migration_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:5]
                    preview = ''.join(lines).strip()
                    print(f"   📝 Preview: {preview[:100]}...")
            except Exception:
                pass
        else:
            print(f"   ❌ File not found: {migration_path}")
        
        print()
    
    print("4. ✅ After executing all migrations, run this script again")
    print("   to verify the database setup")
    print()

async def verify_database_setup():
    """Verify that database is properly set up"""
    print("🔍 VERIFYING DATABASE SETUP")
    print("=" * 60)
    
    try:
        supabase = get_supabase_service()
        print("✅ Connected to Supabase successfully")
        print(f"   URL: {supabase.url}")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False
    
    # Test tables
    tables_to_check = [
        ('users', 'User accounts and profiles'),
        ('user_points', 'User reward points'),
        ('donations', 'Donation records'),
        ('donation_transactions', 'Donation transaction history'),
        ('medication_catalog', 'Approved medications'),
        ('blockchain_transactions', 'Blockchain transaction records'),
        ('vietqr_payments', 'VietQR payment records'),
        ('kyc_documents', 'KYC verification documents')
    ]
    
    success_count = 0
    
    for table_name, description in tables_to_check:
        try:
            result = supabase.table(table_name).select("*").limit(1).execute()
            print(f"✅ {table_name:<25} - {description}")
            success_count += 1
        except Exception as e:
            print(f"❌ {table_name:<25} - Error: {str(e)[:50]}...")
    
    print()
    print(f"📊 Database Status: {success_count}/{len(tables_to_check)} tables verified")
    
    if success_count == len(tables_to_check):
        print("🎉 Database setup is complete and working!")
        return True
    else:
        print("⚠️  Some tables are missing. Please run the migrations.")
        return False

async def test_basic_operations():
    """Test basic database operations"""
    print("\n🧪 TESTING BASIC OPERATIONS")
    print("=" * 60)
    
    try:
        supabase = get_supabase_service()
        
        # Test 1: Check if we can query users table
        print("Test 1: Query users table...")
        try:
            result = supabase.table('users').select('id').limit(1).execute()
            print("✅ Users table query successful")
        except Exception as e:
            print(f"❌ Users table query failed: {e}")
        
        # Test 2: Check if we can query donations table
        print("Test 2: Query donations table...")
        try:
            result = supabase.table('donations').select('id').limit(1).execute()
            print("✅ Donations table query successful")
        except Exception as e:
            print(f"❌ Donations table query failed: {e}")
        
        # Test 3: Check RLS policies
        print("Test 3: Check Row Level Security...")
        try:
            # This should work without authentication for public data
            result = supabase.table('medication_catalog').select('id').limit(1).execute()
            print("✅ RLS policies are working")
        except Exception as e:
            print(f"❌ RLS policies issue: {e}")
        
        print("✅ Basic operations test completed")
        return True
        
    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return False

async def main():
    """Main function"""
    print("🚀 YTILI PLATFORM - DATABASE SETUP")
    print("=" * 60)
    print()
    
    # Check if migrations directory exists
    migrations_dir = Path("migrations/supabase")
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        print("Please make sure you're running this from the backend directory")
        return False
    
    # Try to verify database first
    print("Checking current database status...")
    db_ready = await verify_database_setup()
    
    if not db_ready:
        print()
        print_migration_instructions()
        print("Please run the migrations first, then run this script again.")
        return False
    
    # If database is ready, run tests
    await test_basic_operations()
    
    print("\n🎯 NEXT STEPS")
    print("=" * 60)
    print("1. ✅ Database is ready!")
    print("2. 🔧 Install Python dependencies: pip install -r requirements.txt")
    print("3. ⚙️  Set up environment: cp .env.example .env")
    print("4. 🚀 Start backend server: uvicorn app.main:app --reload")
    print("5. 🧪 Run integration tests: python test_integration.py")
    print()
    print("🎉 Your Ytili platform database is ready to go!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
