-- Ytili Platform - Supabase Migration Script 003
-- Create Fundraising Campaign tables
-- This script creates tables for managing fundraising campaigns

-- Create ENUM types for campaigns
CREATE TYPE campaign_status AS ENUM ('pending', 'active', 'completed', 'cancelled', 'suspended');
CREATE TYPE urgency_level AS ENUM ('urgent', 'high', 'normal', 'low');
CREATE TYPE donation_status AS ENUM ('pending', 'completed', 'failed', 'refunded');

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Campaign details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL, -- emergency_medical, children_health, surgery_treatment, hospital_equipment
    
    -- Financial details
    target_amount DECIMAL(15,2) NOT NULL CHECK (target_amount > 0),
    current_amount DECIMAL(15,2) DEFAULT 0 CHECK (current_amount >= 0),
    currency VARCHAR(3) DEFAULT 'VND',
    
    -- Beneficiary information
    beneficiary_name VARCHAR(255) NOT NULL,
    beneficiary_story TEXT,
    
    -- Status and timing
    status campaign_status DEFAULT 'pending',
    urgency_level urgency_level DEFAULT 'normal',
    start_date TIMESTAMPTZ DEFAULT NOW(),
    end_date TIMESTAMPTZ NOT NULL,
    
    -- Statistics
    donor_count INTEGER DEFAULT 0 CHECK (donor_count >= 0),
    view_count INTEGER DEFAULT 0 CHECK (view_count >= 0),
    share_count INTEGER DEFAULT 0 CHECK (share_count >= 0),
    
    -- Media and documents
    images JSONB DEFAULT '[]'::jsonb, -- Array of image URLs
    medical_documents JSONB DEFAULT '[]'::jsonb, -- Array of document URLs
    
    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES users(id),
    verification_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_end_date CHECK (end_date > start_date),
    CONSTRAINT valid_amounts CHECK (current_amount <= target_amount)
);

-- Create campaign_donations table
CREATE TABLE IF NOT EXISTS campaign_donations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    donor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Donation details
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'VND',
    message TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    
    -- Payment details
    payment_method VARCHAR(50), -- vietqr, bank_transfer, cash, etc.
    payment_reference VARCHAR(255),
    transaction_id VARCHAR(255),
    
    -- Status
    status donation_status DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate donations (same user, same campaign, same amount, same time)
    UNIQUE(campaign_id, donor_id, amount, created_at)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_category ON campaigns(category);
CREATE INDEX IF NOT EXISTS idx_campaigns_urgency ON campaigns(urgency_level);
CREATE INDEX IF NOT EXISTS idx_campaigns_creator ON campaigns(creator_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_end_date ON campaigns(end_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_at ON campaigns(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_campaign_donations_campaign ON campaign_donations(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_donations_donor ON campaign_donations(donor_id);
CREATE INDEX IF NOT EXISTS idx_campaign_donations_status ON campaign_donations(status);
CREATE INDEX IF NOT EXISTS idx_campaign_donations_created_at ON campaign_donations(created_at DESC);

-- Create function to update campaign totals when donations are added
CREATE OR REPLACE FUNCTION update_campaign_totals()
RETURNS TRIGGER AS $$
BEGIN
    -- Update campaign current_amount and donor_count
    UPDATE campaigns 
    SET 
        current_amount = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM campaign_donations 
            WHERE campaign_id = NEW.campaign_id AND status = 'completed'
        ),
        donor_count = (
            SELECT COUNT(DISTINCT donor_id) 
            FROM campaign_donations 
            WHERE campaign_id = NEW.campaign_id AND status = 'completed'
        ),
        updated_at = NOW()
    WHERE id = NEW.campaign_id;
    
    -- Check if campaign target is reached and update status
    UPDATE campaigns 
    SET status = 'completed'
    WHERE id = NEW.campaign_id 
        AND status = 'active' 
        AND current_amount >= target_amount;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update campaign totals
CREATE TRIGGER trigger_update_campaign_totals
    AFTER INSERT OR UPDATE OF status ON campaign_donations
    FOR EACH ROW
    EXECUTE FUNCTION update_campaign_totals();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER trigger_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_campaign_donations_updated_at
    BEFORE UPDATE ON campaign_donations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to check campaign end dates and auto-close expired campaigns
CREATE OR REPLACE FUNCTION close_expired_campaigns()
RETURNS void AS $$
BEGIN
    UPDATE campaigns 
    SET status = 'completed'
    WHERE status = 'active' 
        AND end_date < NOW();
END;
$$ LANGUAGE plpgsql;

-- Insert sample campaign categories (for reference)
INSERT INTO campaigns (
    creator_id, title, description, category, target_amount, beneficiary_name, 
    beneficiary_story, end_date, status, urgency_level
) VALUES 
(
    (SELECT id FROM users WHERE email = 'admin@ytili.com' LIMIT 1),
    'Heart Surgery for 8-Year-Old Mai',
    'Mai needs urgent heart surgery. Her family cannot afford the $15,000 operation cost.',
    'emergency_medical',
    15000.00,
    'Mai Nguyen',
    'Mai is a bright 8-year-old girl who loves to draw and play with her friends. She was born with a congenital heart defect that requires immediate surgical intervention. Her family has exhausted all their savings and is desperately seeking help from the community.',
    NOW() + INTERVAL '30 days',
    'active',
    'urgent'
),
(
    (SELECT id FROM users WHERE email = 'admin@ytili.com' LIMIT 1),
    'Mobile Medical Unit for Rural Areas',
    'Bringing healthcare to remote villages with a fully equipped mobile medical unit.',
    'hospital_equipment',
    50000.00,
    'Rural Healthcare Initiative',
    'Many villages in remote areas lack access to basic healthcare. This mobile medical unit will provide essential medical services, vaccinations, and health screenings to underserved communities.',
    NOW() + INTERVAL '60 days',
    'active',
    'high'
),
(
    (SELECT id FROM users WHERE email = 'admin@ytili.com' LIMIT 1),
    'Cancer Treatment for Teacher Linh',
    'Supporting a beloved teacher''s cancer treatment and recovery journey.',
    'surgery_treatment',
    20000.00,
    'Linh Tran',
    'Teacher Linh has dedicated her life to educating children in our community. Now she needs our support as she battles cancer. The treatment costs are overwhelming for her family.',
    NOW() + INTERVAL '45 days',
    'active',
    'normal'
)
ON CONFLICT DO NOTHING;

-- Create RLS (Row Level Security) policies
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_donations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view all active campaigns
CREATE POLICY "Anyone can view active campaigns" ON campaigns
    FOR SELECT USING (status = 'active');

-- Policy: Users can view their own campaigns
CREATE POLICY "Users can view own campaigns" ON campaigns
    FOR SELECT USING (creator_id = auth.uid());

-- Policy: Verified users can create campaigns
CREATE POLICY "Verified users can create campaigns" ON campaigns
    FOR INSERT WITH CHECK (
        creator_id = auth.uid() AND
        EXISTS (
            SELECT 1 FROM users 
            WHERE id = auth.uid() AND status = 'verified'
        )
    );

-- Policy: Users can update their own campaigns
CREATE POLICY "Users can update own campaigns" ON campaigns
    FOR UPDATE USING (creator_id = auth.uid());

-- Policy: Users can view donations to campaigns they created
CREATE POLICY "Campaign creators can view donations" ON campaign_donations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM campaigns 
            WHERE id = campaign_id AND creator_id = auth.uid()
        )
    );

-- Policy: Users can view their own donations
CREATE POLICY "Users can view own donations" ON campaign_donations
    FOR SELECT USING (donor_id = auth.uid());

-- Policy: Verified users can donate to campaigns
CREATE POLICY "Verified users can donate" ON campaign_donations
    FOR INSERT WITH CHECK (
        donor_id = auth.uid() AND
        EXISTS (
            SELECT 1 FROM users 
            WHERE id = auth.uid() AND status = 'verified'
        ) AND
        EXISTS (
            SELECT 1 FROM campaigns 
            WHERE id = campaign_id AND status = 'active'
        )
    );

-- Grant necessary permissions
GRANT ALL ON campaigns TO authenticated;
GRANT ALL ON campaign_donations TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
