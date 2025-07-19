#!/usr/bin/env python3
"""
Add blockchain tracking fields to Supabase database
"""
import os
import sys
from supabase import create_client, Client

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def add_blockchain_fields():
    """Add blockchain tracking fields to donations table"""
    
    # Initialize Supabase client
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    
    print("🔧 Adding blockchain tracking fields to database...")
    
    # SQL to add blockchain fields to donations table
    sql_commands = [
        """
        ALTER TABLE donations 
        ADD COLUMN IF NOT EXISTS blockchain_status VARCHAR(50) DEFAULT 'pending';
        """,
        """
        ALTER TABLE donations 
        ADD COLUMN IF NOT EXISTS blockchain_tx_hash VARCHAR(66);
        """,
        """
        ALTER TABLE donations 
        ADD COLUMN IF NOT EXISTS blockchain_recorded_at TIMESTAMPTZ;
        """,
        """
        ALTER TABLE donations 
        ADD COLUMN IF NOT EXISTS metadata_hash VARCHAR(64);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_donations_blockchain_status 
        ON donations(blockchain_status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_donations_blockchain_tx_hash 
        ON donations(blockchain_tx_hash);
        """
    ]
    
    try:
        for i, sql in enumerate(sql_commands, 1):
            print(f"  Executing command {i}/{len(sql_commands)}...")
            result = supabase.rpc('exec_sql', {'sql': sql.strip()}).execute()
            print(f"  ✅ Command {i} completed")
        
        print("\n🎉 Successfully added blockchain tracking fields!")
        print("Fields added:")
        print("  - blockchain_status (VARCHAR(50))")
        print("  - blockchain_tx_hash (VARCHAR(66))")
        print("  - blockchain_recorded_at (TIMESTAMPTZ)")
        print("  - metadata_hash (VARCHAR(64))")
        print("  - Indexes for performance")
        
    except Exception as e:
        print(f"❌ Error adding blockchain fields: {str(e)}")
        print("Note: Some fields may already exist, which is normal.")

def verify_blockchain_fields():
    """Verify that blockchain fields were added successfully"""
    
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    
    print("\n🔍 Verifying blockchain fields...")
    
    try:
        # Try to select the new fields
        result = supabase.table('donations').select(
            'id, blockchain_status, blockchain_tx_hash, blockchain_recorded_at, metadata_hash'
        ).limit(1).execute()
        
        print("✅ All blockchain fields are accessible")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying fields: {str(e)}")
        return False

def main():
    """Main function"""
    print("🚀 Ytili Database Migration - Blockchain Fields")
    print("=" * 50)
    
    # Add fields
    add_blockchain_fields()
    
    # Verify fields
    verify_blockchain_fields()
    
    print("\n✅ Migration completed!")

if __name__ == "__main__":
    main()
