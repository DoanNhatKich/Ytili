-- Ytili Platform - Supabase Migration Script 002
-- Create Donations, DonationTransactions, and MedicationCatalog tables
-- This script migrates the existing donation system to Supabase

-- Create ENUM types for donations
CREATE TYPE donation_type AS ENUM ('medication', 'medical_supply', 'food', 'cash');
CREATE TYPE donation_status AS ENUM ('pending', 'verified', 'matched', 'shipped', 'delivered', 'completed', 'cancelled');
CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'refunded');

-- Donations table (main donation records)
CREATE TABLE IF NOT EXISTS donations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Parties involved
    donor_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    recipient_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Donation details
    donation_type donation_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- For medication/supply donations
    item_name VARCHAR(255),
    quantity INTEGER,
    unit VARCHAR(50),
    expiry_date TIMESTAMP WITH TIME ZONE,
    batch_number VARCHAR(100),
    manufacturer VARCHAR(255),
    
    -- For cash donations
    amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'VND',
    
    -- Status tracking
    status donation_status DEFAULT 'pending',
    payment_status payment_status DEFAULT 'pending',
    
    -- Verification and quality control
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by UUID REFERENCES users(id),
    
    -- Logistics
    pickup_address TEXT,
    delivery_address TEXT,
    tracking_number VARCHAR(100),
    
    -- Metadata
    images JSONB,
    documents JSONB,
    notes TEXT,
    
    -- Points and rewards
    points_awarded INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Donation Transactions table (blockchain-inspired transparency)
CREATE TABLE IF NOT EXISTS donation_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    donation_id UUID REFERENCES donations(id) ON DELETE CASCADE NOT NULL,
    
    -- Transaction details
    transaction_type VARCHAR(50) NOT NULL,
    description TEXT,
    
    -- Actor
    actor_id UUID REFERENCES users(id),
    actor_type VARCHAR(50),
    
    -- Metadata
    metadata JSONB,
    
    -- Blockchain-style hash for integrity
    transaction_hash VARCHAR(64) UNIQUE NOT NULL,
    previous_hash VARCHAR(64),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Medication Catalog table (approved medications and supplies)
CREATE TABLE IF NOT EXISTS medication_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    brand_names JSONB,
    
    -- Classification
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    therapeutic_class VARCHAR(100),
    
    -- Regulatory
    registration_number VARCHAR(100),
    is_prescription_required BOOLEAN DEFAULT FALSE,
    is_controlled_substance BOOLEAN DEFAULT FALSE,
    
    -- Physical properties
    dosage_form VARCHAR(100),
    strength VARCHAR(100),
    packaging VARCHAR(100),
    
    -- Usage info
    indications TEXT,
    contraindications TEXT,
    side_effects TEXT,
    storage_conditions TEXT,
    
    -- Donation guidelines
    min_expiry_months INTEGER DEFAULT 6,
    is_donation_allowed BOOLEAN DEFAULT TRUE,
    donation_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- New tables for enhanced features

-- Blockchain Transactions table (for Saga integration)
CREATE TABLE IF NOT EXISTS blockchain_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    donation_id UUID REFERENCES donations(id) ON DELETE CASCADE,
    
    -- Blockchain details
    blockchain_hash VARCHAR(66) UNIQUE NOT NULL, -- 0x + 64 chars
    block_number BIGINT,
    transaction_index INTEGER,
    gas_used BIGINT,
    gas_price BIGINT,
    
    -- Contract interaction
    contract_address VARCHAR(42),
    function_name VARCHAR(100),
    function_params JSONB,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, confirmed, failed
    confirmations INTEGER DEFAULT 0,
    
    -- Metadata
    network_id VARCHAR(50) DEFAULT 'ytili_saga',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE
);

-- VietQR Payments table (for Vietnamese payment integration)
CREATE TABLE IF NOT EXISTS vietqr_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    donation_id UUID REFERENCES donations(id) ON DELETE CASCADE,
    
    -- VietQR details
    qr_code_id VARCHAR(100) UNIQUE,
    bank_id VARCHAR(10),
    account_number VARCHAR(50),
    account_name VARCHAR(255),
    
    -- Payment details
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'VND',
    content TEXT,
    
    -- QR Code
    qr_data_url TEXT,
    qr_code TEXT,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending', -- pending, paid, expired, cancelled
    payment_reference VARCHAR(100),
    bank_transaction_id VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_donations_donor_id ON donations(donor_id);
CREATE INDEX IF NOT EXISTS idx_donations_recipient_id ON donations(recipient_id);
CREATE INDEX IF NOT EXISTS idx_donations_status ON donations(status);
CREATE INDEX IF NOT EXISTS idx_donations_donation_type ON donations(donation_type);
CREATE INDEX IF NOT EXISTS idx_donations_created_at ON donations(created_at);

CREATE INDEX IF NOT EXISTS idx_donation_transactions_donation_id ON donation_transactions(donation_id);
CREATE INDEX IF NOT EXISTS idx_donation_transactions_hash ON donation_transactions(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_donation_transactions_created_at ON donation_transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_medication_catalog_name ON medication_catalog(name);
CREATE INDEX IF NOT EXISTS idx_medication_catalog_category ON medication_catalog(category);
CREATE INDEX IF NOT EXISTS idx_medication_catalog_donation_allowed ON medication_catalog(is_donation_allowed);

CREATE INDEX IF NOT EXISTS idx_blockchain_transactions_donation_id ON blockchain_transactions(donation_id);
CREATE INDEX IF NOT EXISTS idx_blockchain_transactions_hash ON blockchain_transactions(blockchain_hash);
CREATE INDEX IF NOT EXISTS idx_blockchain_transactions_status ON blockchain_transactions(status);

CREATE INDEX IF NOT EXISTS idx_vietqr_payments_donation_id ON vietqr_payments(donation_id);
CREATE INDEX IF NOT EXISTS idx_vietqr_payments_qr_code_id ON vietqr_payments(qr_code_id);
CREATE INDEX IF NOT EXISTS idx_vietqr_payments_status ON vietqr_payments(status);

-- Apply updated_at triggers
CREATE TRIGGER update_donations_updated_at BEFORE UPDATE ON donations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medication_catalog_updated_at BEFORE UPDATE ON medication_catalog
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE donations ENABLE ROW LEVEL SECURITY;
ALTER TABLE donation_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE medication_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE blockchain_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vietqr_payments ENABLE ROW LEVEL SECURITY;

-- Donations table policies
CREATE POLICY "Users can view their own donations" ON donations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = donations.donor_id 
            AND users.auth_user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = donations.recipient_id 
            AND users.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create donations" ON donations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = donations.donor_id 
            AND users.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "Donors can update their donations" ON donations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = donations.donor_id 
            AND users.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "Hospitals can view available donations" ON donations
    FOR SELECT USING (
        donations.status = 'verified' 
        AND donations.recipient_id IS NULL
    );

CREATE POLICY "Government users can view all donations" ON donations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE auth_user_id = auth.uid() 
            AND user_type = 'government' 
            AND status = 'verified'
        )
    );

-- Donation Transactions policies (public for transparency)
CREATE POLICY "Anyone can view donation transactions" ON donation_transactions
    FOR SELECT USING (TRUE);

CREATE POLICY "System can insert transactions" ON donation_transactions
    FOR INSERT WITH CHECK (TRUE); -- Restricted by service role

-- Medication Catalog policies (public read)
CREATE POLICY "Anyone can view medication catalog" ON medication_catalog
    FOR SELECT USING (TRUE);

CREATE POLICY "Government users can manage catalog" ON medication_catalog
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE auth_user_id = auth.uid() 
            AND user_type = 'government' 
            AND status = 'verified'
        )
    );

-- Blockchain Transactions policies
CREATE POLICY "Users can view blockchain transactions for their donations" ON blockchain_transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM donations 
            JOIN users ON (users.id = donations.donor_id OR users.id = donations.recipient_id)
            WHERE donations.id = blockchain_transactions.donation_id 
            AND users.auth_user_id = auth.uid()
        )
    );

-- VietQR Payments policies
CREATE POLICY "Users can view their payment records" ON vietqr_payments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM donations 
            JOIN users ON users.id = donations.donor_id
            WHERE donations.id = vietqr_payments.donation_id 
            AND users.auth_user_id = auth.uid()
        )
    );