-- Ytili Platform - Supabase Migration Script 001
-- Create Users, UserPoints, and KYCDocuments tables
-- This script migrates the existing user management system to Supabase

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types
CREATE TYPE user_type AS ENUM ('individual', 'hospital', 'organization', 'government');
CREATE TYPE user_status AS ENUM ('pending', 'verified', 'suspended', 'rejected');

-- Users table (main user information)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    
    -- Basic info
    full_name VARCHAR(255) NOT NULL,
    user_type user_type NOT NULL,
    status user_status DEFAULT 'pending',
    
    -- Verification flags
    is_email_verified BOOLEAN DEFAULT FALSE,
    is_phone_verified BOOLEAN DEFAULT FALSE,
    is_kyc_verified BOOLEAN DEFAULT FALSE,
    
    -- Organization specific fields
    organization_name VARCHAR(255),
    license_number VARCHAR(100),
    tax_id VARCHAR(50),
    
    -- Location
    address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Vietnam',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Supabase Auth integration
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- User Points table (rewards and points system)
CREATE TABLE IF NOT EXISTS user_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    
    total_points INTEGER DEFAULT 0,
    available_points INTEGER DEFAULT 0,
    lifetime_earned INTEGER DEFAULT 0,
    lifetime_spent INTEGER DEFAULT 0,
    
    -- Tier system
    tier_level VARCHAR(20) DEFAULT 'Bronze',
    
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- KYC Documents table (Know Your Customer verification)
CREATE TABLE IF NOT EXISTS kyc_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    
    document_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    
    -- OCR extracted data
    extracted_data JSONB,
    
    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by UUID REFERENCES users(id),
    rejection_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_user_points_user_id ON user_points(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_documents_user_id ON kyc_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_documents_verified ON kyc_documents(is_verified);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_points_updated_at BEFORE UPDATE ON user_points
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE kyc_documents ENABLE ROW LEVEL SECURITY;

-- Users table policies
CREATE POLICY "Users can view their own profile" ON users
    FOR SELECT USING (auth.uid() = auth_user_id);

CREATE POLICY "Users can update their own profile" ON users
    FOR UPDATE USING (auth.uid() = auth_user_id);

CREATE POLICY "Government users can view all users" ON users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE auth_user_id = auth.uid() 
            AND user_type = 'government' 
            AND status = 'verified'
        )
    );

CREATE POLICY "Government users can update user status" ON users
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE auth_user_id = auth.uid() 
            AND user_type = 'government' 
            AND status = 'verified'
        )
    );

-- User Points table policies
CREATE POLICY "Users can view their own points" ON user_points
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = user_points.user_id 
            AND users.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "System can update user points" ON user_points
    FOR ALL USING (TRUE); -- Will be restricted by service role

-- KYC Documents table policies
CREATE POLICY "Users can view their own KYC documents" ON kyc_documents
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = kyc_documents.user_id 
            AND users.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert their own KYC documents" ON kyc_documents
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = kyc_documents.user_id 
            AND users.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "Government users can view all KYC documents" ON kyc_documents
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE auth_user_id = auth.uid() 
            AND user_type = 'government' 
            AND status = 'verified'
        )
    );

CREATE POLICY "Government users can verify KYC documents" ON kyc_documents
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE auth_user_id = auth.uid() 
            AND user_type = 'government' 
            AND status = 'verified'
        )
    );

-- Create database functions for common operations

-- Function to get user by auth_user_id
CREATE OR REPLACE FUNCTION get_user_by_auth_id(auth_user_id UUID)
RETURNS users AS $$
DECLARE
    user_record users;
BEGIN
    SELECT * INTO user_record FROM users WHERE users.auth_user_id = get_user_by_auth_id.auth_user_id;
    RETURN user_record;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create user points record
CREATE OR REPLACE FUNCTION create_user_points(user_id UUID)
RETURNS user_points AS $$
DECLARE
    points_record user_points;
BEGIN
    INSERT INTO user_points (user_id) VALUES (create_user_points.user_id)
    RETURNING * INTO points_record;
    RETURN points_record;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to verify user permissions
CREATE OR REPLACE FUNCTION verify_user_permissions(user_id UUID, permission TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    user_record users;
BEGIN
    SELECT * INTO user_record FROM users WHERE id = verify_user_permissions.user_id;
    
    IF user_record IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check based on permission type
    CASE permission
        WHEN 'admin' THEN
            RETURN user_record.user_type = 'government' AND user_record.status = 'verified';
        WHEN 'hospital' THEN
            RETURN user_record.user_type = 'hospital' AND user_record.status = 'verified';
        WHEN 'verified' THEN
            RETURN user_record.status = 'verified';
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
