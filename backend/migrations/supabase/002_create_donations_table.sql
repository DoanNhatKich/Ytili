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

INSERT INTO medication_catalog (name, generic_name, brand_names, category, subcategory, therapeutic_class, is_prescription_required, dosage_form, strength, packaging, indications, storage_conditions, min_expiry_months, is_donation_allowed) VALUES
('Paracetamol', 'Acetaminophen', '["Tylenol", "Panadol", "Efferalgan"]', 'medication', 'analgesic', 'Non-opioid analgesic', false, 'tablet', '500mg', 'box of 20 tablets', 'Pain relief, fever reduction', 'Store below 30°C', 12, true),
('Amoxicillin', 'Amoxicillin', '["Augmentin", "Amoxil", "Clamoxyl"]', 'medication', 'antibiotic', 'Penicillin antibiotic', true, 'capsule', '500mg', 'box of 21 capsules', 'Bacterial infections', 'Store below 25°C', 18, true),
('Insulin', 'Human Insulin', '["Humulin", "Novolin", "Lantus"]', 'medication', 'hormone', 'Antidiabetic hormone', true, 'injection', '100 IU/ml', 'vial 10ml', 'Diabetes mellitus type 1 and 2', 'Refrigerate 2-8°C', 6, true),
('Vitamin C', 'Ascorbic Acid', '["Redoxon", "Cebion", "Vitamin C 1000"]', 'supplement', 'vitamin', 'Water-soluble vitamin', false, 'tablet', '1000mg', 'bottle of 30 tablets', 'Immune support, antioxidant', 'Store in dry place', 24, true),
('Medical Bandages', 'Sterile Gauze Bandage', '["Johnson & Johnson", "3M Nexcare"]', 'medical_supply', 'wound_care', 'Wound dressing material', false, 'roll', '5cm x 5m', 'individual sterile pack', 'Wound dressing and protection', 'Store in dry place', 36, true);

INSERT INTO donations (donor_id, recipient_id, donation_type, title, description, item_name, quantity, unit, amount, currency, status, payment_status, pickup_address, delivery_address, points_awarded) VALUES
((SELECT id FROM users WHERE email = 'donor1@gmail.com'), (SELECT id FROM users WHERE email = 'doctor@benhviencho.vn'), 'medication', 'Thuốc kháng sinh cho khoa nhi', 'Amoxicillin 500mg cho trẻ em bị nhiễm khuẩn', 'Amoxicillin', 100, 'capsules', 850000, 'VND', 'completed', 'completed', '123 Nguyen Trai, Q1, TPHCM', '2 Nguyen Thong, Q3, TPHCM', 150),
((SELECT id FROM users WHERE email = 'csr@vingroup.vn'), (SELECT id FROM users WHERE email = 'doctor@benhviencho.vn'), 'cash', 'Hỗ trợ mua thiết bị y tế', 'Đóng góp tiền mặt để mua máy đo huyết áp', null, null, null, 10000000, 'VND', 'verified', 'completed', null, '2 Nguyen Thong, Q3, TPHCM', 200),
((SELECT id FROM users WHERE email = 'donor1@gmail.com'), (SELECT id FROM users WHERE email = 'pharmacy@pharmacity.vn'), 'medication', 'Insulin khẩn cấp', 'Insulin cho bệnh nhân tiểu đường type 1', 'Insulin', 5, 'vials', 2250000, 'VND', 'shipped', 'completed', '456 Le Van Sy, Q3, TPHCM', '789 Hai Ba Trung, Q1, TPHCM', 300),
((SELECT id FROM users WHERE email = 'admin@ytili.com'), (SELECT id FROM users WHERE email = 'doctor@benhviencho.vn'), 'medical_supply', 'Băng y tế cho khoa cấp cứu', 'Băng gạc vô trùng cho khoa cấp cứu', 'Medical Bandages', 200, 'rolls', 700000, 'VND', 'delivered', 'completed', 'Ytili Warehouse, Q7, TPHCM', '2 Nguyen Thong, Q3, TPHCM', 100),
((SELECT id FROM users WHERE email = 'csr@vingroup.vn'), (SELECT id FROM users WHERE email = 'pharmacy@pharmacity.vn'), 'medication', 'Vitamin tăng cường sức khỏe', 'Vitamin C cho người cao tuổi', 'Vitamin C', 50, 'bottles', 600000, 'VND', 'pending', 'pending', null, '789 Hai Ba Trung, Q1, TPHCM', 0);

INSERT INTO donation_transactions (donation_id, transaction_type, description, actor_id, actor_type, metadata, transaction_hash, previous_hash) VALUES
((SELECT id FROM donations WHERE title = 'Thuốc kháng sinh cho khoa nhi'), 'creation', 'Donation created and verified', (SELECT id FROM users WHERE email = 'donor1@gmail.com'), 'donor', '{"verification_method": "manual", "verifier": "admin", "amount": 850000, "currency": "VND"}', '1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890', null),
((SELECT id FROM donations WHERE title = 'Thuốc kháng sinh cho khoa nhi'), 'status_update', 'Donation accepted by hospital', (SELECT id FROM users WHERE email = 'doctor@benhviencho.vn'), 'recipient', '{"acceptance_date": "2024-01-15", "expected_delivery": "2024-01-20", "new_status": "matched"}', '2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890ab', '1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890'),
((SELECT id FROM donations WHERE title = 'Hỗ trợ mua thiết bị y tế'), 'creation', 'Corporate donation created', (SELECT id FROM users WHERE email = 'csr@vingroup.vn'), 'donor', '{"corporate_program": "healthcare_support", "tax_deductible": true, "amount": 10000000, "currency": "VND"}', '3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcd', null),
((SELECT id FROM donations WHERE title = 'Insulin khẩn cấp'), 'creation', 'Emergency insulin donation', (SELECT id FROM users WHERE email = 'donor1@gmail.com'), 'donor', '{"urgency_level": "critical", "expiry_check": "passed", "amount": 2250000, "currency": "VND"}', '4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef', null),
((SELECT id FROM donations WHERE title = 'Băng y tế cho khoa cấp cứu'), 'delivery', 'Donation delivered successfully', (SELECT id FROM users WHERE email = 'admin@ytili.com'), 'platform', '{"delivery_date": "2024-01-18", "recipient_confirmation": true, "amount": 700000, "currency": "VND"}', '5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12', '4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef');

INSERT INTO blockchain_transactions (donation_id, blockchain_hash, network_id, block_number, gas_used, status, contract_address, function_name, function_params) VALUES
((SELECT id FROM donations WHERE title = 'Thuốc kháng sinh cho khoa nhi'), '0x1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890', 'ytili_saga', 12345678, 21000, 'confirmed', '0x96c394B6B709Ac81a3Eef1c1B94ceB4372bBE487', 'recordDonation', '{"donation_id": "donation_uuid", "donor_id": "donor_uuid", "donation_type": 0, "title": "Thuốc kháng sinh cho khoa nhi"}'),
((SELECT id FROM donations WHERE title = 'Hỗ trợ mua thiết bị y tế'), '0x3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcd', 'ytili_saga', 12345680, 25000, 'confirmed', '0x96c394B6B709Ac81a3Eef1c1B94ceB4372bBE487', 'recordDonation', '{"donation_id": "donation_uuid", "donor_id": "donor_uuid", "donation_type": 3, "title": "Hỗ trợ mua thiết bị y tế"}'),
((SELECT id FROM donations WHERE title = 'Insulin khẩn cấp'), '0x4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef', 'ytili_saga', 12345682, 23000, 'confirmed', '0x96c394B6B709Ac81a3Eef1c1B94ceB4372bBE487', 'recordDonation', '{"donation_id": "donation_uuid", "donor_id": "donor_uuid", "donation_type": 0, "title": "Insulin khẩn cấp"}'),
((SELECT id FROM donations WHERE title = 'Băng y tế cho khoa cấp cứu'), '0x5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12', 'ytili_saga', 12345684, 22000, 'confirmed', '0x96c394B6B709Ac81a3Eef1c1B94ceB4372bBE487', 'updateDonationStatus', '{"donation_id": "donation_uuid", "new_status": 4, "actor_type": "platform"}'),
((SELECT id FROM donations WHERE title = 'Thuốc kháng sinh cho khoa nhi'), '0x6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234', 'ytili_saga', 12345686, 18000, 'confirmed', '0x66C06efE9B8B44940379F5c53328a35a3Abc3Fe7', 'mint', '{"recipient": "donor_address", "amount": "100000000000000000000", "reason": "donation_reward"}');

INSERT INTO vietqr_payments (donation_id, qr_code_id, bank_id, account_number, account_name, amount, currency, content, qr_data_url, qr_code, status, payment_reference, bank_transaction_id, paid_at) VALUES
((SELECT id FROM donations WHERE title = 'Thuốc kháng sinh cho khoa nhi'), 'YTILI_001_A1B2C3D4', '970415', '113366668888', 'YTILI PLATFORM', 850000, 'VND', 'Thuoc khang sinh cho khoa nhi - Ref: YTILI_001_A1B2C3D4', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEA...', '00020101021238570010A000000727012700069704150113366668888020850000530370454088500005802VN62230819Thuoc khang sinh6304ABCD', 'paid', 'YTILI_001_A1B2C3D4', 'VTB20240115103045001', '2024-01-15 10:35:00+07'),
((SELECT id FROM donations WHERE title = 'Hỗ trợ mua thiết bị y tế'), 'YTILI_002_E5F6G7H8', '970415', '113366668888', 'YTILI PLATFORM', 10000000, 'VND', 'Ho tro mua thiet bi y te - Ref: YTILI_002_E5F6G7H8', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEA...', '00020101021238570010A000000727012700069704150113366668888021000000530370454101000000005802VN62230819Ho tro mua thiet bi6304EFGH', 'paid', 'YTILI_002_E5F6G7H8', 'VTB20240116142130002', '2024-01-16 14:25:00+07'),
((SELECT id FROM donations WHERE title = 'Insulin khẩn cấp'), 'YTILI_003_I9J0K1L2', '970415', '113366668888', 'YTILI PLATFORM', 2250000, 'VND', 'Insulin khan cap - Ref: YTILI_003_I9J0K1L2', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEA...', '00020101021238570010A000000727012700069704150113366668888022500005303704540922500005802VN62230819Insulin khan cap6304IJKL', 'paid', 'YTILI_003_I9J0K1L2', 'VTB20240117091820003', '2024-01-17 09:20:00+07'),
((SELECT id FROM donations WHERE title = 'Băng y tế cho khoa cấp cứu'), 'YTILI_004_M3N4O5P6', '970415', '113366668888', 'YTILI PLATFORM', 700000, 'VND', 'Bang y te cho khoa cap cuu - Ref: YTILI_004_M3N4O5P6', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEA...', '00020101021238570010A000000727012700069704150113366668888070000053037045407700005802VN62230819Bang y te cho khoa6304MNOP', 'paid', 'YTILI_004_M3N4O5P6', 'VTB20240118164800004', '2024-01-18 16:50:00+07'),
((SELECT id FROM donations WHERE title = 'Vitamin tăng cường sức khỏe'), 'YTILI_005_Q7R8S9T0', '970415', '113366668888', 'YTILI PLATFORM', 600000, 'VND', 'Vitamin tang cuong suc khoe - Ref: YTILI_005_Q7R8S9T0', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEA...', '00020101021238570010A000000727012700069704150113366668888060000053037045406600005802VN62230819Vitamin tang cuong6304QRST', 'pending', 'YTILI_005_Q7R8S9T0', null, null);