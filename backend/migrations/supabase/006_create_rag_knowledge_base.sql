-- Migration 006: Create RAG Knowledge Base for Ytili AI Agent
-- This migration creates tables for storing medical knowledge and enabling semantic search

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create knowledge base table for medical information
CREATE TABLE IF NOT EXISTS rag_knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL DEFAULT 'medical_info', -- medical_info, drug_info, hospital_info, procedure_info
    category VARCHAR(100), -- cardiology, pediatrics, emergency, etc.
    subcategory VARCHAR(100), -- specific conditions, drug classes, etc.
    language VARCHAR(10) DEFAULT 'vi', -- vi for Vietnamese, en for English
    source VARCHAR(200), -- WHO, Ministry of Health Vietnam, medical journals, etc.
    source_url TEXT,
    keywords TEXT[], -- Array of keywords for better search
    embedding vector(384), -- Sentence transformer embeddings (384 dimensions)
    metadata JSONB DEFAULT '{}', -- Additional structured data
    is_verified BOOLEAN DEFAULT false, -- Medical professional verification
    verified_by VARCHAR(100), -- Who verified this information
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_content_type ON rag_knowledge_base(content_type);
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_category ON rag_knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_language ON rag_knowledge_base(language);
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_keywords ON rag_knowledge_base USING GIN(keywords);
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_metadata ON rag_knowledge_base USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_verified ON rag_knowledge_base(is_verified);

-- Create vector similarity search index
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_embedding ON rag_knowledge_base 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create full-text search index for Vietnamese content
CREATE INDEX IF NOT EXISTS idx_rag_knowledge_content_fts ON rag_knowledge_base 
USING gin(to_tsvector('simple', content));

-- Create table for conversation context enhancement
CREATE TABLE IF NOT EXISTS rag_conversation_context (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE CASCADE,
    knowledge_base_ids INTEGER[] DEFAULT '{}', -- Array of knowledge base IDs used
    context_summary TEXT, -- Summary of retrieved context
    relevance_scores FLOAT[] DEFAULT '{}', -- Relevance scores for each knowledge item
    retrieval_query TEXT, -- The query used for retrieval
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for conversation context
CREATE INDEX IF NOT EXISTS idx_rag_conversation_context_conv_id ON rag_conversation_context(conversation_id);

-- Create function for semantic search
CREATE OR REPLACE FUNCTION search_knowledge_semantic(
    query_embedding vector(384),
    content_type_filter VARCHAR(50) DEFAULT NULL,
    category_filter VARCHAR(100) DEFAULT NULL,
    language_filter VARCHAR(10) DEFAULT 'vi',
    limit_results INTEGER DEFAULT 5,
    similarity_threshold DOUBLE PRECISION DEFAULT 0.3  -- Giảm threshold từ 0.7 xuống 0.3
)
RETURNS TABLE(
    id INTEGER,
    title VARCHAR(500),
    content TEXT,
    content_type VARCHAR(50),
    category VARCHAR(100),
    similarity_score DOUBLE PRECISION,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kb.id,
        kb.title,
        kb.content,
        kb.content_type,
        kb.category,
        (1 - (kb.embedding <=> query_embedding))::DOUBLE PRECISION as similarity_score,
        kb.metadata
    FROM rag_knowledge_base kb
    WHERE 
        kb.embedding IS NOT NULL  -- Đảm bảo có embedding
        AND (content_type_filter IS NULL OR kb.content_type = content_type_filter)
        AND (category_filter IS NULL OR kb.category = category_filter)
        AND (language_filter IS NULL OR kb.language = language_filter)
        AND kb.is_verified = true
        AND (1 - (kb.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Create function for hybrid search (semantic + keyword)
CREATE OR REPLACE FUNCTION search_knowledge_hybrid(
    query_text TEXT,
    query_embedding vector(384),
    content_type_filter VARCHAR(50) DEFAULT NULL,
    category_filter VARCHAR(100) DEFAULT NULL,
    language_filter VARCHAR(10) DEFAULT 'vi',
    limit_results INTEGER DEFAULT 5,
    semantic_weight DOUBLE PRECISION DEFAULT 0.7,
    keyword_weight DOUBLE PRECISION DEFAULT 0.3
)
RETURNS TABLE(
    id INTEGER,
    title VARCHAR(500),
    content TEXT,
    content_type VARCHAR(50),
    category VARCHAR(100),
    combined_score FLOAT,
    semantic_score FLOAT,
    keyword_score FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kb.id,
        kb.title,
        kb.content,
        kb.content_type,
        kb.category,
        (semantic_weight * (1 - (kb.embedding <=> query_embedding)) + 
         keyword_weight * ts_rank(to_tsvector('simple', kb.content), plainto_tsquery('simple', query_text))) as combined_score,
        1 - (kb.embedding <=> query_embedding) as semantic_score,
        ts_rank(to_tsvector('simple', kb.content), plainto_tsquery('simple', query_text)) as keyword_score,
        kb.metadata
    FROM rag_knowledge_base kb
    WHERE 
        (content_type_filter IS NULL OR kb.content_type = content_type_filter)
        AND (category_filter IS NULL OR kb.category = category_filter)
        AND (language_filter IS NULL OR kb.language = language_filter)
        AND kb.is_verified = true
        AND (
            (1 - (kb.embedding <=> query_embedding)) >= 0.6 
            OR to_tsvector('simple', kb.content) @@ plainto_tsquery('simple', query_text)
        )
    ORDER BY combined_score DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Insert initial Vietnamese medical knowledge
INSERT INTO rag_knowledge_base (title, content, content_type, category, subcategory, language, source, keywords, is_verified, verified_by, verified_at) VALUES
('Triệu chứng cảm cúm thông thường', 'Cảm cúm thông thường có các triệu chứng: sốt nhẹ (37-38°C), ho khan, chảy nước mũi, hắt hơi, đau họng nhẹ, mệt mỏi. Thường kéo dài 3-7 ngày và tự khỏi. Cần uống nhiều nước, nghỉ ngơi đầy đủ. Nếu sốt cao trên 38.5°C hoặc khó thở cần đến bệnh viện.', 'medical_info', 'general_medicine', 'respiratory', 'vi', 'Bộ Y tế Việt Nam', ARRAY['cảm cúm', 'sốt', 'ho', 'chảy nước mũi', 'đau họng'], true, 'medical_team', CURRENT_TIMESTAMP),

('Sơ cứu bỏng độ 1', 'Bỏng độ 1 (bỏng nông): da đỏ, sưng, đau nhưng không có vết loét. Sơ cứu: Rửa ngay bằng nước mát (15-20°C) trong 10-20 phút. Không dùng nước đá. Có thể thoa gel lô hội hoặc kem bỏng. Tránh chọc vỡ phồng rộp nếu có. Nếu diện tích bỏng lớn hơn lòng bàn tay cần đến bệnh viện.', 'medical_info', 'emergency', 'burns', 'vi', 'Hội Cấp cứu Việt Nam', ARRAY['bỏng', 'sơ cứu', 'nước mát', 'gel lô hội'], true, 'emergency_team', CURRENT_TIMESTAMP),

('Paracetamol - Thuốc hạ sốt giảm đau', 'Paracetamol (Acetaminophen) là thuốc hạ sốt, giảm đau phổ biến. Liều dùng người lớn: 500-1000mg mỗi 4-6 giờ, tối đa 4000mg/ngày. Trẻ em: 10-15mg/kg cân nặng mỗi 4-6 giờ. Tác dụng phụ hiếm gặp nhưng có thể gây độc gan nếu dùng quá liều. Không dùng cho người bệnh gan nặng.', 'drug_info', 'analgesics', 'paracetamol', 'vi', 'Cục Quản lý Dược', ARRAY['paracetamol', 'hạ sốt', 'giảm đau', 'acetaminophen'], true, 'pharmacist', CURRENT_TIMESTAMP),

('Bệnh viện Chợ Rẫy - Thông tin cơ bản', 'Bệnh viện Chợ Rẫy là bệnh viện đa khoa hạng đặc biệt tại TP.HCM. Địa chỉ: 201B Nguyễn Chí Thanh, Quận 5. Điện thoại: (028) 38554269. Chuyên khoa mạnh: Tim mạch, Thần kinh, Cấp cứu, Ghép tạng. Hoạt động 24/7. Có khoa cấp cứu và ICU hiện đại.', 'hospital_info', 'major_hospitals', 'cho_ray', 'vi', 'Bộ Y tế', ARRAY['Chợ Rẫy', 'bệnh viện', 'TP.HCM', 'cấp cứu', 'tim mạch'], true, 'hospital_admin', CURRENT_TIMESTAMP),

('Quy trình quyên góp thuốc an toàn', 'Quy trình quyên góp thuốc qua Ytili: 1) Kiểm tra hạn sử dụng (còn ít nhất 6 tháng), 2) Chụp ảnh bao bì rõ nét, 3) Điền thông tin đầy đủ trên app, 4) Chờ xác minh từ dược sĩ, 5) Giao thuốc tại điểm thu gom hoặc nhà thuốc đối tác. Không nhận thuốc đã mở seal, thuốc kê đơn đặc biệt, thuốc gây nghiện.', 'procedure_info', 'donation_process', 'drug_donation', 'vi', 'Ytili Platform', ARRAY['quyên góp', 'thuốc', 'hạn sử dụng', 'xác minh', 'dược sĩ'], true, 'ytili_team', CURRENT_TIMESTAMP);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_rag_knowledge_base_updated_at 
    BEFORE UPDATE ON rag_knowledge_base 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON rag_knowledge_base TO authenticated;
GRANT SELECT, INSERT, UPDATE ON rag_conversation_context TO authenticated;
GRANT USAGE ON SEQUENCE rag_knowledge_base_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE rag_conversation_context_id_seq TO authenticated;

-- Create RLS policies
ALTER TABLE rag_knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_conversation_context ENABLE ROW LEVEL SECURITY;

-- Policy for reading verified knowledge
CREATE POLICY "Allow reading verified knowledge" ON rag_knowledge_base
    FOR SELECT USING (is_verified = true);

-- Policy for conversation context (users can only access their own)
CREATE POLICY "Users can access their conversation context" ON rag_conversation_context
    FOR ALL USING (
        conversation_id IN (
            SELECT id FROM ai_conversations WHERE user_id = auth.uid()
        )
    );

COMMENT ON TABLE rag_knowledge_base IS 'Medical knowledge base for RAG-enhanced AI responses';
COMMENT ON TABLE rag_conversation_context IS 'Context tracking for AI conversations with knowledge retrieval';

-- Assuming you want to insert into a profiles table linked to auth.users
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    phone TEXT,
    user_type TEXT DEFAULT 'individual',
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Modify the profiles table to add a unique constraint on user_id
ALTER TABLE public.profiles 
ADD CONSTRAINT unique_user_id UNIQUE (user_id);

-- Insert the test user
INSERT INTO public.profiles (user_id, email, full_name, phone, user_type, is_verified) 
VALUES (
    auth.uid(),
    auth.email(),
    'Test User',
    '+84123456789',
    'individual',
    true
) ON CONFLICT (user_id) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    phone = EXCLUDED.phone,
    user_type = EXCLUDED.user_type,
    is_verified = EXCLUDED.is_verified;

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow users to see their own profile
CREATE POLICY "Users can view own profile" 
ON public.profiles FOR SELECT 
USING (auth.uid() = user_id);