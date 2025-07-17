-- AI Agent Tables for Ytili Platform
-- Creates tables for AI conversations, recommendations, emergency requests, and analytics

-- AI Conversations table
CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    conversation_type VARCHAR(50) NOT NULL CHECK (conversation_type IN ('donation_advisory', 'medical_info', 'campaign_help', 'emergency_request', 'general_support')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'escalated', 'archived')),
    title VARCHAR(255),
    context_data JSONB DEFAULT '{}',
    conversation_metadata JSONB DEFAULT '{}',
    total_messages INTEGER DEFAULT 0,
    avg_response_time FLOAT,
    user_satisfaction_score FLOAT CHECK (user_satisfaction_score >= 1 AND user_satisfaction_score <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- AI Messages table
CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'feedback')),
    content TEXT NOT NULL,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    response_time FLOAT,
    message_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI Recommendations table
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE SET NULL,
    recommendation_type VARCHAR(50) NOT NULL CHECK (recommendation_type IN ('donation_match', 'campaign_suggestion', 'hospital_priority', 'emergency_routing', 'fraud_alert')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    recommendation_data JSONB DEFAULT '{}',
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    is_viewed BOOLEAN DEFAULT FALSE,
    is_accepted BOOLEAN DEFAULT FALSE,
    user_feedback TEXT,
    was_successful BOOLEAN,
    success_metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    viewed_at TIMESTAMP WITH TIME ZONE,
    acted_upon_at TIMESTAMP WITH TIME ZONE
);

-- Emergency Requests table
CREATE TABLE IF NOT EXISTS emergency_requests (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE SET NULL,
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    medical_condition VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    location TEXT,
    contact_phone VARCHAR(20),
    ai_assessment JSONB DEFAULT '{}',
    recommended_actions JSONB DEFAULT '[]',
    is_responded BOOLEAN DEFAULT FALSE,
    response_time_minutes INTEGER,
    assigned_hospital_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'in_progress', 'resolved', 'cancelled')),
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- AI Analytics table
CREATE TABLE IF NOT EXISTS ai_analytics (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    period_type VARCHAR(20) NOT NULL CHECK (period_type IN ('hourly', 'daily', 'weekly', 'monthly')),
    total_conversations INTEGER DEFAULT 0,
    avg_conversation_length FLOAT,
    avg_response_time FLOAT,
    avg_satisfaction_score FLOAT,
    total_feedback_count INTEGER DEFAULT 0,
    total_recommendations INTEGER DEFAULT 0,
    recommendation_acceptance_rate FLOAT,
    recommendation_success_rate FLOAT,
    total_emergency_requests INTEGER DEFAULT 0,
    avg_emergency_response_time FLOAT,
    emergency_resolution_rate FLOAT,
    total_tokens_used INTEGER DEFAULT 0,
    total_api_calls INTEGER DEFAULT 0,
    api_error_rate FLOAT,
    estimated_cost DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Medical Knowledge Base table
CREATE TABLE IF NOT EXISTS medical_knowledge_base (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('condition', 'treatment', 'drug', 'procedure')),
    name VARCHAR(255) NOT NULL,
    vietnamese_name VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    specialty VARCHAR(100),
    description TEXT,
    symptoms JSONB DEFAULT '[]',
    treatments JSONB DEFAULT '[]',
    medications JSONB DEFAULT '[]',
    related_conditions JSONB DEFAULT '[]',
    contraindications JSONB DEFAULT '[]',
    drug_interactions JSONB DEFAULT '[]',
    is_emergency_condition BOOLEAN DEFAULT FALSE,
    emergency_actions JSONB DEFAULT '[]',
    keywords JSONB DEFAULT '[]',
    synonyms JSONB DEFAULT '[]',
    source VARCHAR(255),
    last_verified TIMESTAMP WITH TIME ZONE,
    confidence_level FLOAT CHECK (confidence_level >= 0 AND confidence_level <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document Verifications table
CREATE TABLE IF NOT EXISTS document_verifications (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_path VARCHAR(500) NOT NULL,
    verification_score INTEGER CHECK (verification_score >= 0 AND verification_score <= 100),
    confidence_level VARCHAR(20) CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high', 'very_high')),
    extracted_text TEXT,
    text_analysis JSONB DEFAULT '{}',
    authenticity_check JSONB DEFAULT '{}',
    requires_manual_review BOOLEAN DEFAULT FALSE,
    verification_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fraud Analysis table
-- Fraud Analysis table with flexible campaign_id
CREATE TABLE IF NOT EXISTS fraud_analysis (
    id SERIAL PRIMARY KEY,
    campaign_id UUID, -- Changed to UUID and made nullable
    fraud_score INTEGER CHECK (fraud_score >= 0 AND fraud_score <= 100),
    risk_level VARCHAR(20) CHECK (risk_level IN ('minimal', 'low', 'medium', 'high', 'critical')),
    fraud_indicators JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    requires_manual_review BOOLEAN DEFAULT FALSE,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_session_id ON ai_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_type ON ai_conversations(conversation_type);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_status ON ai_conversations(status);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_created_at ON ai_conversations(created_at);

CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_id ON ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_role ON ai_messages(role);
CREATE INDEX IF NOT EXISTS idx_ai_messages_created_at ON ai_messages(created_at);

CREATE INDEX IF NOT EXISTS idx_ai_recommendations_user_id ON ai_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_conversation_id ON ai_recommendations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_type ON ai_recommendations(recommendation_type);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_viewed ON ai_recommendations(is_viewed);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_accepted ON ai_recommendations(is_accepted);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_created_at ON ai_recommendations(created_at);

CREATE INDEX IF NOT EXISTS idx_emergency_requests_user_id ON emergency_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_emergency_requests_priority ON emergency_requests(priority);
CREATE INDEX IF NOT EXISTS idx_emergency_requests_status ON emergency_requests(status);
CREATE INDEX IF NOT EXISTS idx_emergency_requests_created_at ON emergency_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_emergency_requests_responded ON emergency_requests(is_responded);

CREATE INDEX IF NOT EXISTS idx_ai_analytics_date ON ai_analytics(date);
CREATE INDEX IF NOT EXISTS idx_ai_analytics_period_type ON ai_analytics(period_type);

CREATE INDEX IF NOT EXISTS idx_medical_knowledge_entity_type ON medical_knowledge_base(entity_type);
CREATE INDEX IF NOT EXISTS idx_medical_knowledge_name ON medical_knowledge_base(name);
CREATE INDEX IF NOT EXISTS idx_medical_knowledge_vietnamese_name ON medical_knowledge_base(vietnamese_name);
CREATE INDEX IF NOT EXISTS idx_medical_knowledge_category ON medical_knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_medical_knowledge_specialty ON medical_knowledge_base(specialty);
CREATE INDEX IF NOT EXISTS idx_medical_knowledge_emergency ON medical_knowledge_base(is_emergency_condition);

CREATE INDEX IF NOT EXISTS idx_document_verifications_user_id ON document_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_document_verifications_score ON document_verifications(verification_score);
CREATE INDEX IF NOT EXISTS idx_document_verifications_manual_review ON document_verifications(requires_manual_review);

CREATE INDEX IF NOT EXISTS idx_fraud_analysis_campaign_id ON fraud_analysis(campaign_id);
CREATE INDEX IF NOT EXISTS idx_fraud_analysis_risk_level ON fraud_analysis(risk_level);
CREATE INDEX IF NOT EXISTS idx_fraud_analysis_manual_review ON fraud_analysis(requires_manual_review);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_ai_conversations_updated_at BEFORE UPDATE ON ai_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_medical_knowledge_base_updated_at BEFORE UPDATE ON medical_knowledge_base FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to increment total_messages in ai_conversations
CREATE OR REPLACE FUNCTION increment_total_messages(conversation_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    new_count INTEGER;
BEGIN
    UPDATE ai_conversations 
    SET total_messages = total_messages + 1,
        updated_at = NOW()
    WHERE id = conversation_id;
    
    SELECT total_messages INTO new_count 
    FROM ai_conversations 
    WHERE id = conversation_id;
    
    RETURN new_count;
END;
$$ LANGUAGE plpgsql;

-- Insert some sample medical knowledge data
INSERT INTO medical_knowledge_base (entity_type, name, vietnamese_name, category, specialty, description, symptoms, is_emergency_condition, keywords, synonyms) VALUES
('condition', 'Heart Disease', 'Bệnh tim', 'cardiovascular', 'cardiology', 'Các bệnh lý liên quan đến tim và mạch máu', '["đau ngực", "khó thở", "mệt mỏi", "đánh trống ngực"]', true, '["tim", "cardiac", "heart", "tim mạch"]', '["bệnh tim", "tim mạch", "đau tim"]'),
('condition', 'Diabetes', 'Tiểu đường', 'endocrine', 'endocrinology', 'Bệnh rối loạn chuyển hóa đường trong máu', '["khát nước nhiều", "tiểu nhiều", "mệt mỏi", "sụt cân"]', false, '["diabetes", "tiểu đường", "đái tháo đường"]', '["tiểu đường", "đái tháo đường", "diabetes"]'),
('condition', 'Cancer', 'Ung thư', 'oncology', 'oncology', 'Các bệnh lý ung thư và khối u ác tính', '["sụt cân", "mệt mỏi", "đau không rõ nguyên nhân"]', false, '["cancer", "ung thư", "khối u", "tumor"]', '["ung thư", "cancer", "khối u", "u ác tính"]'),
('condition', 'Stroke', 'Đột quỵ', 'neurological', 'neurology', 'Tình trạng thiếu máu não hoặc xuất huyết não', '["liệt nửa người", "nói khó", "mất ý thức", "đau đầu dữ dội"]', true, '["stroke", "đột quỵ", "tai biến mạch máu não"]', '["đột quỵ", "stroke", "tai biến mạch máu não"]'),
('condition', 'Dengue Fever', 'Sốt xuất huyết', 'infectious', 'infectious_disease', 'Bệnh nhiễm trùng do virus dengue', '["sốt cao", "đau đầu", "đau cơ", "nôn mửa", "chảy máu"]', true, '["dengue", "sốt xuất huyết", "sốt dengue"]', '["sốt xuất huyết", "dengue fever", "sốt dengue"]');

-- Grant necessary permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
