-- Ytili Platform - Supabase Migration Script 003
-- Create database functions for complex operations
-- This script creates stored procedures and functions for business logic

-- Function to get complete donation transaction chain
CREATE OR REPLACE FUNCTION get_donation_chain(donation_id UUID)
RETURNS TABLE (
    id UUID,
    transaction_type VARCHAR(50),
    description TEXT,
    actor_id UUID,
    actor_type VARCHAR(50),
    actor_name VARCHAR(255),
    metadata JSONB,
    transaction_hash VARCHAR(64),
    previous_hash VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dt.id,
        dt.transaction_type,
        dt.description,
        dt.actor_id,
        dt.actor_type,
        COALESCE(u.full_name, u.organization_name, 'System') as actor_name,
        dt.metadata,
        dt.transaction_hash,
        dt.previous_hash,
        dt.created_at
    FROM donation_transactions dt
    LEFT JOIN users u ON dt.actor_id = u.id
    WHERE dt.donation_id = get_donation_chain.donation_id
    ORDER BY dt.created_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to calculate transparency score for a donation
CREATE OR REPLACE FUNCTION calculate_transparency_score(donation_id UUID)
RETURNS DECIMAL(5,2) AS $$
DECLARE
    transaction_count INTEGER;
    verified_actors INTEGER;
    chain_integrity BOOLEAN;
    score DECIMAL(5,2) := 0;
BEGIN
    -- Count total transactions
    SELECT COUNT(*) INTO transaction_count
    FROM donation_transactions dt
    WHERE dt.donation_id = calculate_transparency_score.donation_id;
    
    -- Count verified actors
    SELECT COUNT(DISTINCT dt.actor_id) INTO verified_actors
    FROM donation_transactions dt
    JOIN users u ON dt.actor_id = u.id
    WHERE dt.donation_id = calculate_transparency_score.donation_id
    AND u.status = 'verified';
    
    -- Check chain integrity (simplified)
    SELECT COUNT(*) = 0 INTO chain_integrity
    FROM (
        SELECT dt1.id
        FROM donation_transactions dt1
        JOIN donation_transactions dt2 ON dt2.previous_hash = dt1.transaction_hash
        WHERE dt1.donation_id = calculate_transparency_score.donation_id
        AND dt2.donation_id = calculate_transparency_score.donation_id
        AND dt1.created_at < dt2.created_at
    ) broken_links;
    
    -- Calculate score
    -- Base score for having transactions
    IF transaction_count > 0 THEN
        score := score + 20;
    END IF;
    
    -- Score for chain integrity
    IF chain_integrity THEN
        score := score + 30;
    END IF;
    
    -- Score for number of transactions
    IF transaction_count >= 5 THEN
        score := score + 25;
    ELSIF transaction_count >= 3 THEN
        score := score + 15;
    ELSIF transaction_count >= 1 THEN
        score := score + 10;
    END IF;
    
    -- Score for verified actors
    IF verified_actors > 0 AND transaction_count > 0 THEN
        score := score + LEAST(25, (verified_actors::DECIMAL / transaction_count) * 25);
    END IF;
    
    RETURN LEAST(100, score);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get platform statistics
CREATE OR REPLACE FUNCTION get_platform_statistics()
RETURNS TABLE (
    total_donations BIGINT,
    total_transactions BIGINT,
    total_users BIGINT,
    donations_by_status JSONB,
    donations_by_type JSONB,
    average_transparency_score DECIMAL(5,2)
) AS $$
DECLARE
    status_counts JSONB;
    type_counts JSONB;
    avg_score DECIMAL(5,2);
BEGIN
    -- Get total counts
    SELECT COUNT(*) INTO total_donations FROM donations;
    SELECT COUNT(*) INTO total_transactions FROM donation_transactions;
    SELECT COUNT(*) INTO total_users FROM users;
    
    -- Get donations by status
    SELECT jsonb_object_agg(status, count)
    INTO status_counts
    FROM (
        SELECT status::TEXT, COUNT(*) as count
        FROM donations
        GROUP BY status
    ) status_data;
    
    -- Get donations by type
    SELECT jsonb_object_agg(donation_type, count)
    INTO type_counts
    FROM (
        SELECT donation_type::TEXT, COUNT(*) as count
        FROM donations
        GROUP BY donation_type
    ) type_data;
    
    -- Calculate average transparency score
    SELECT AVG(calculate_transparency_score(d.id))
    INTO avg_score
    FROM donations d;
    
    RETURN QUERY SELECT 
        get_platform_statistics.total_donations,
        get_platform_statistics.total_transactions,
        get_platform_statistics.total_users,
        status_counts,
        type_counts,
        COALESCE(avg_score, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to find matching hospitals for a donation
CREATE OR REPLACE FUNCTION find_matching_hospitals(donation_id UUID, max_results INTEGER DEFAULT 10)
RETURNS TABLE (
    hospital_id UUID,
    hospital_name VARCHAR(255),
    match_score DECIMAL(5,2),
    distance_km DECIMAL(8,2),
    recent_donations INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id as hospital_id,
        COALESCE(u.organization_name, u.full_name) as hospital_name,
        -- Simplified match score calculation
        CASE 
            WHEN u.city = d.pickup_address THEN 50.0
            WHEN u.province = d.pickup_address THEN 30.0
            ELSE 10.0
        END as match_score,
        0.0 as distance_km, -- Placeholder for actual distance calculation
        (
            SELECT COUNT(*)::INTEGER
            FROM donations recent_d
            WHERE recent_d.recipient_id = u.id
            AND recent_d.created_at > NOW() - INTERVAL '30 days'
        ) as recent_donations
    FROM users u
    CROSS JOIN donations d
    WHERE u.user_type = 'hospital'
    AND u.status = 'verified'
    AND d.id = find_matching_hospitals.donation_id
    ORDER BY match_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create donation transaction with hash
CREATE OR REPLACE FUNCTION create_donation_transaction(
    p_donation_id UUID,
    p_transaction_type VARCHAR(50),
    p_description TEXT,
    p_actor_id UUID,
    p_actor_type VARCHAR(50),
    p_metadata JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    previous_tx_hash VARCHAR(64);
    new_tx_hash VARCHAR(64);
    new_tx_id UUID;
    tx_data TEXT;
BEGIN
    -- Get the previous transaction hash
    SELECT transaction_hash INTO previous_tx_hash
    FROM donation_transactions
    WHERE donation_id = p_donation_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- If no previous transaction, use zeros
    IF previous_tx_hash IS NULL THEN
        previous_tx_hash := REPEAT('0', 64);
    END IF;
    
    -- Generate new transaction ID
    new_tx_id := uuid_generate_v4();
    
    -- Create transaction data for hashing
    tx_data := p_donation_id::TEXT || p_transaction_type || p_description || 
               COALESCE(p_actor_id::TEXT, '') || p_actor_type || 
               COALESCE(p_metadata::TEXT, '{}') || previous_tx_hash || 
               EXTRACT(EPOCH FROM NOW())::TEXT;
    
    -- Generate hash (simplified - in production use proper cryptographic hash)
    new_tx_hash := encode(digest(tx_data, 'sha256'), 'hex');
    
    -- Insert the transaction
    INSERT INTO donation_transactions (
        id, donation_id, transaction_type, description, 
        actor_id, actor_type, metadata, transaction_hash, previous_hash
    ) VALUES (
        new_tx_id, p_donation_id, p_transaction_type, p_description,
        p_actor_id, p_actor_type, p_metadata, new_tx_hash, previous_tx_hash
    );
    
    RETURN new_tx_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to verify donation chain integrity
CREATE OR REPLACE FUNCTION verify_donation_chain_integrity(donation_id UUID)
RETURNS TABLE (
    is_valid BOOLEAN,
    total_transactions INTEGER,
    broken_links INTEGER,
    invalid_hashes INTEGER
) AS $$
DECLARE
    tx_count INTEGER;
    broken_count INTEGER;
    invalid_count INTEGER;
BEGIN
    -- Count total transactions
    SELECT COUNT(*) INTO tx_count
    FROM donation_transactions
    WHERE donation_transactions.donation_id = verify_donation_chain_integrity.donation_id;
    
    -- Count broken chain links
    SELECT COUNT(*) INTO broken_count
    FROM donation_transactions dt1
    LEFT JOIN donation_transactions dt2 ON dt2.previous_hash = dt1.transaction_hash
    WHERE dt1.donation_id = verify_donation_chain_integrity.donation_id
    AND dt1.created_at < (
        SELECT MAX(created_at) 
        FROM donation_transactions 
        WHERE donation_transactions.donation_id = verify_donation_chain_integrity.donation_id
    )
    AND dt2.id IS NULL;
    
    -- Count invalid hashes (simplified check)
    SELECT COUNT(*) INTO invalid_count
    FROM donation_transactions
    WHERE donation_transactions.donation_id = verify_donation_chain_integrity.donation_id
    AND (transaction_hash IS NULL OR LENGTH(transaction_hash) != 64);
    
    RETURN QUERY SELECT 
        (broken_count = 0 AND invalid_count = 0) as is_valid,
        tx_count as total_transactions,
        broken_count as broken_links,
        invalid_count as invalid_hashes;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update user points
CREATE OR REPLACE FUNCTION update_user_points(
    p_user_id UUID,
    p_points_change INTEGER,
    p_reason TEXT DEFAULT 'Manual adjustment'
)
RETURNS BOOLEAN AS $$
DECLARE
    current_points INTEGER;
    new_total INTEGER;
    new_available INTEGER;
BEGIN
    -- Get current points
    SELECT total_points, available_points 
    INTO current_points, new_available
    FROM user_points
    WHERE user_id = p_user_id;
    
    -- If user doesn't have points record, create one
    IF NOT FOUND THEN
        INSERT INTO user_points (user_id, total_points, available_points, lifetime_earned)
        VALUES (p_user_id, GREATEST(0, p_points_change), GREATEST(0, p_points_change), GREATEST(0, p_points_change));
        RETURN TRUE;
    END IF;
    
    -- Calculate new values
    new_total := current_points + p_points_change;
    new_available := new_available + p_points_change;
    
    -- Ensure points don't go negative
    IF new_available < 0 THEN
        RETURN FALSE;
    END IF;
    
    -- Update points
    UPDATE user_points
    SET 
        total_points = new_total,
        available_points = new_available,
        lifetime_earned = CASE 
            WHEN p_points_change > 0 THEN lifetime_earned + p_points_change
            ELSE lifetime_earned
        END,
        lifetime_spent = CASE 
            WHEN p_points_change < 0 THEN lifetime_spent + ABS(p_points_change)
            ELSE lifetime_spent
        END,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user fraud risk score
CREATE OR REPLACE FUNCTION calculate_user_fraud_risk(p_user_id UUID)
RETURNS TABLE (
    risk_score INTEGER,
    risk_level VARCHAR(10),
    risk_factors JSONB
) AS $$
DECLARE
    user_record users;
    account_age_days INTEGER;
    donation_count INTEGER;
    failed_payments INTEGER;
    rejected_kyc INTEGER;
    score INTEGER := 0;
    factors JSONB := '[]'::JSONB;
    level VARCHAR(10);
BEGIN
    -- Get user record
    SELECT * INTO user_record FROM users WHERE id = p_user_id;
    
    IF user_record IS NULL THEN
        RETURN QUERY SELECT 0, 'unknown'::VARCHAR(10), '["User not found"]'::JSONB;
        RETURN;
    END IF;
    
    -- Calculate account age
    account_age_days := EXTRACT(DAY FROM NOW() - user_record.created_at);
    
    -- Account age factor
    IF account_age_days < 7 THEN
        score := score + 20;
        factors := factors || jsonb_build_array('New account (' || account_age_days || ' days old)');
    ELSIF account_age_days < 30 THEN
        score := score + 10;
        factors := factors || jsonb_build_array('Recent account (' || account_age_days || ' days old)');
    END IF;
    
    -- Verification status
    IF user_record.status != 'verified' THEN
        score := score + 25;
        factors := factors || jsonb_build_array('Account not fully verified');
    END IF;
    
    IF NOT user_record.is_email_verified THEN
        score := score + 15;
        factors := factors || jsonb_build_array('Email not verified');
    END IF;
    
    -- Get donation count
    SELECT COUNT(*) INTO donation_count FROM donations WHERE donor_id = p_user_id;
    
    IF donation_count = 0 THEN
        score := score + 5;
        factors := factors || jsonb_build_array('No donation history');
    END IF;
    
    -- Get failed payments
    SELECT COUNT(*) INTO failed_payments 
    FROM donations 
    WHERE donor_id = p_user_id AND payment_status = 'failed';
    
    IF failed_payments > 0 THEN
        score := score + LEAST(failed_payments * 10, 30);
        factors := factors || jsonb_build_array(failed_payments || ' failed payment(s)');
    END IF;
    
    -- Get rejected KYC documents
    SELECT COUNT(*) INTO rejected_kyc
    FROM kyc_documents
    WHERE user_id = p_user_id AND is_verified = FALSE AND rejection_reason IS NOT NULL;
    
    IF rejected_kyc > 0 THEN
        score := score + LEAST(rejected_kyc * 15, 45);
        factors := factors || jsonb_build_array(rejected_kyc || ' rejected KYC document(s)');
    END IF;
    
    -- Cap score at 100
    score := LEAST(score, 100);
    
    -- Determine risk level
    IF score >= 75 THEN
        level := 'high';
    ELSIF score >= 40 THEN
        level := 'medium';
    ELSE
        level := 'low';
    END IF;
    
    RETURN QUERY SELECT score, level, factors;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;