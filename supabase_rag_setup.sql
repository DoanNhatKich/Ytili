-- RAG Knowledge Base Setup for Ytili AI Agent
-- Run this SQL in Supabase SQL Editor

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create knowledge base table for medical information
CREATE TABLE IF NOT EXISTS rag_knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL DEFAULT 'medical_info',
    category VARCHAR(100),
    subcategory VARCHAR(100),
    language VARCHAR(10) DEFAULT 'vi',
    source VARCHAR(200),
    source_url TEXT,
    keywords TEXT[],
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    is_verified BOOLEAN DEFAULT false,
    verified_by VARCHAR(100),
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
    knowledge_base_ids INTEGER[] DEFAULT '{}',
    context_summary TEXT,
    relevance_scores DOUBLE PRECISION[] DEFAULT '{}',
    retrieval_query TEXT,
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
    similarity_threshold DOUBLE PRECISION DEFAULT 0.7
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
        (content_type_filter IS NULL OR kb.content_type = content_type_filter)
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
    combined_score DOUBLE PRECISION,
    semantic_score DOUBLE PRECISION,
    keyword_score DOUBLE PRECISION,
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
        (semantic_weight * (1 - (kb.embedding <=> query_embedding))::DOUBLE PRECISION + 
         keyword_weight * ts_rank(to_tsvector('simple', kb.content), plainto_tsquery('simple', query_text))::DOUBLE PRECISION)::DOUBLE PRECISION as combined_score,
        (1 - (kb.embedding <=> query_embedding))::DOUBLE PRECISION as semantic_score,
        ts_rank(to_tsvector('simple', kb.content), plainto_tsquery('simple', query_text))::DOUBLE PRECISION as keyword_score,
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
            SELECT id FROM ai_conversations WHERE user_id = auth.uid()::text
        )
    );

COMMENT ON TABLE rag_knowledge_base IS 'Medical knowledge base for RAG-enhanced AI responses';
COMMENT ON TABLE rag_conversation_context IS 'Context tracking for AI conversations with knowledge retrieval';
