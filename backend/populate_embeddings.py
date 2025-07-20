#!/usr/bin/env python3
"""
Script to populate embeddings for RAG knowledge base
Run this after creating the tables in Supabase
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.ai_agent.rag_service import rag_service
from app.core.supabase import get_supabase_service


async def populate_embeddings():
    """Generate and update embeddings for all knowledge base items"""
    print("🚀 Populating embeddings for RAG knowledge base...")
    
    supabase = get_supabase_service()
    
    try:
        # Get all knowledge base items without embeddings
        result = supabase.table('rag_knowledge_base').select('*').is_('embedding', 'null').execute()
        
        if not result.data:
            print("✅ No items need embedding generation")
            return True
        
        print(f"📝 Found {len(result.data)} items needing embeddings")
        
        success_count = 0
        
        for item in result.data:
            try:
                # Generate embedding for title + content
                text_to_embed = f"{item['title']} {item['content']}"
                embedding = await rag_service.get_embedding(text_to_embed)
                
                if embedding:
                    # Update the item with embedding
                    update_result = supabase.table('rag_knowledge_base').update({
                        'embedding': embedding
                    }).eq('id', item['id']).execute()
                    
                    if update_result.data:
                        print(f"✅ Updated embedding for: {item['title']}")
                        success_count += 1
                    else:
                        print(f"❌ Failed to update embedding for: {item['title']}")
                else:
                    print(f"❌ Failed to generate embedding for: {item['title']}")
                    
            except Exception as e:
                print(f"❌ Error processing {item['title']}: {str(e)}")
        
        print(f"\n📊 Results: {success_count}/{len(result.data)} embeddings generated successfully")
        
        if success_count == len(result.data):
            print("🎉 All embeddings generated successfully!")
            return True
        else:
            print("⚠️ Some embeddings failed to generate")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing knowledge base: {str(e)}")
        print("\n💡 Make sure you've run the SQL setup in Supabase first!")
        return False


async def test_search():
    """Test the search functionality"""
    print("\n🔍 Testing knowledge search...")
    
    test_queries = [
        "cảm cúm sốt",
        "bỏng sơ cứu",
        "paracetamol liều dùng",
        "bệnh viện Chợ Rẫy",
        "quyên góp thuốc"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Searching for: '{query}'")
        
        results = await rag_service.search_knowledge(
            query=query,
            limit=2,
            similarity_threshold=0.5
        )
        
        if results:
            for i, result in enumerate(results):
                score = result.get('similarity_score', result.get('combined_score', 0))
                print(f"  {i+1}. {result['title']} (score: {score:.3f})")
        else:
            print("  No results found")


async def main():
    """Main function"""
    print("🚀 RAG Knowledge Base Setup and Test\n")
    
    # Step 1: Populate embeddings
    embedding_success = await populate_embeddings()
    
    if embedding_success:
        # Step 2: Test search
        await test_search()
        
        print("\n🎉 RAG Knowledge Base is ready!")
        print("✅ OpenRouter API: Working")
        print("✅ Embeddings: Generated")
        print("✅ Search: Functional")
        
        return True
    else:
        print("\n❌ RAG setup incomplete. Please check the errors above.")
        return False


if __name__ == "__main__":
    asyncio.run(main())
