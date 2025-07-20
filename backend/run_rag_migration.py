#!/usr/bin/env python3
"""
Simple script to run RAG migration directly in Supabase
"""
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.supabase import get_supabase_service


def run_migration():
    """Run the RAG knowledge base migration by creating sample data"""
    print("🚀 Running RAG Knowledge Base Migration...")

    supabase = get_supabase_service()

    # Since we can't run DDL through Supabase client, let's just create sample data
    # The table should be created manually in Supabase dashboard

    print("📝 Creating sample knowledge base data...")

    sample_data = [
        {
            "title": "Triệu chứng cảm cúm thông thường",
            "content": "Cảm cúm thông thường có các triệu chứng: sốt nhẹ (37-38°C), ho khan, chảy nước mũi, hắt hơi, đau họng nhẹ, mệt mỏi. Thường kéo dài 3-7 ngày và tự khỏi. Cần uống nhiều nước, nghỉ ngơi đầy đủ. Nếu sốt cao trên 38.5°C hoặc khó thở cần đến bệnh viện.",
            "content_type": "medical_info",
            "category": "general_medicine",
            "subcategory": "respiratory",
            "language": "vi",
            "source": "Bộ Y tế Việt Nam",
            "keywords": ["cảm cúm", "sốt", "ho", "chảy nước mũi", "đau họng"],
            "is_verified": True,
            "verified_by": "medical_team",
            "metadata": {"severity": "mild", "duration": "3-7 days"}
        },
        {
            "title": "Sơ cứu bỏng độ 1",
            "content": "Bỏng độ 1 (bỏng nông): da đỏ, sưng, đau nhưng không có vết loét. Sơ cứu: Rửa ngay bằng nước mát (15-20°C) trong 10-20 phút. Không dùng nước đá. Có thể thoa gel lô hội hoặc kem bỏng. Tránh chọc vỡ phồng rộp nếu có. Nếu diện tích bỏng lớn hơn lòng bàn tay cần đến bệnh viện.",
            "content_type": "medical_info",
            "category": "emergency",
            "subcategory": "burns",
            "language": "vi",
            "source": "Hội Cấp cứu Việt Nam",
            "keywords": ["bỏng", "sơ cứu", "nước mát", "gel lô hội"],
            "is_verified": True,
            "verified_by": "emergency_team",
            "metadata": {"burn_degree": 1, "treatment_time": "10-20 minutes"}
        },
        {
            "title": "Paracetamol - Thuốc hạ sốt giảm đau",
            "content": "Paracetamol (Acetaminophen) là thuốc hạ sốt, giảm đau phổ biến. Liều dùng người lớn: 500-1000mg mỗi 4-6 giờ, tối đa 4000mg/ngày. Trẻ em: 10-15mg/kg cân nặng mỗi 4-6 giờ. Tác dụng phụ hiếm gặp nhưng có thể gây độc gan nếu dùng quá liều. Không dùng cho người bệnh gan nặng.",
            "content_type": "drug_info",
            "category": "analgesics",
            "subcategory": "paracetamol",
            "language": "vi",
            "source": "Cục Quản lý Dược",
            "keywords": ["paracetamol", "hạ sốt", "giảm đau", "acetaminophen"],
            "is_verified": True,
            "verified_by": "pharmacist",
            "metadata": {"max_daily_dose": "4000mg", "contraindication": "severe liver disease"}
        }
    ]

    success_count = 0

    # Try to check if table exists first
    try:
        result = supabase.table('rag_knowledge_base').select('id').limit(1).execute()
        print("✅ rag_knowledge_base table exists")

        # Insert sample data
        for i, data in enumerate(sample_data):
            try:
                result = supabase.table('rag_knowledge_base').insert(data).execute()
                if result.data:
                    print(f"✅ Inserted sample data {i+1}: {data['title']}")
                    success_count += 1
                else:
                    print(f"❌ Failed to insert sample data {i+1}: {data['title']}")
            except Exception as e:
                print(f"❌ Error inserting sample data {i+1}: {str(e)}")

    except Exception as e:
        print(f"❌ Table rag_knowledge_base does not exist or error: {str(e)}")
        print("\n📋 Please create the table manually in Supabase with this SQL:")
        print("""
CREATE TABLE rag_knowledge_base (
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
        """)
        return False

    print(f"\n📊 Migration Results: {success_count}/{len(sample_data)} sample records inserted")

    if success_count > 0:
        print("🎉 RAG Knowledge Base sample data created successfully!")
        return True
    else:
        print("⚠️ No sample data was inserted.")
        return False


if __name__ == "__main__":
    run_migration()
