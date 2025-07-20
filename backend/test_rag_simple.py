#!/usr/bin/env python3
"""
Simple test for RAG semantic search
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.ai_agent.rag_service import rag_service
from app.core.supabase import get_supabase_service


async def test_semantic_search_direct():
    """Test semantic search directly"""
    print("🔍 Testing Semantic Search Directly...")
    
    supabase = get_supabase_service()
    
    # Generate embedding for test query
    query = "cảm cúm sốt"
    embedding = await rag_service.get_embedding(query)
    
    if not embedding:
        print("❌ Failed to generate embedding")
        return False
    
    print(f"✅ Generated embedding for '{query}' ({len(embedding)} dimensions)")
    
    # Test direct semantic search function
    try:
        result = supabase.rpc(
            'search_knowledge_semantic',
            {
                'query_embedding': embedding,
                'content_type_filter': None,
                'category_filter': None,
                'language_filter': 'vi',
                'limit_results': 3,
                'similarity_threshold': 0.5
            }
        ).execute()
        
        if result.data:
            print(f"✅ Found {len(result.data)} results:")
            for i, item in enumerate(result.data):
                print(f"  {i+1}. {item['title']} (score: {item['similarity_score']:.3f})")
            return True
        else:
            print("❌ No results found")
            return False
            
    except Exception as e:
        print(f"❌ Semantic search error: {str(e)}")
        return False


async def test_rag_service_search():
    """Test RAG service search method"""
    print("\n📚 Testing RAG Service Search...")
    
    try:
        # Force semantic search only
        results = await rag_service._semantic_search(
            query_embedding=await rag_service.get_embedding("cảm cúm sốt"),
            content_type=None,
            category=None,
            language='vi',
            limit=3,
            similarity_threshold=0.5
        )
        
        if results:
            print(f"✅ RAG service found {len(results)} results:")
            for i, item in enumerate(results):
                print(f"  {i+1}. {item['title']} (score: {item['similarity_score']:.3f})")
            return True
        else:
            print("❌ RAG service found no results")
            return False
            
    except Exception as e:
        print(f"❌ RAG service error: {str(e)}")
        return False


async def test_knowledge_table():
    """Test knowledge table contents"""
    print("\n📋 Testing Knowledge Table Contents...")
    
    supabase = get_supabase_service()
    
    try:
        # Get all items with embeddings
        result = supabase.table('rag_knowledge_base').select('id, title, embedding').is_not('embedding', 'null').execute()
        
        if result.data:
            print(f"✅ Found {len(result.data)} items with embeddings:")
            for item in result.data:
                embedding_length = len(item['embedding']) if item['embedding'] else 0
                print(f"  - {item['title']} (embedding: {embedding_length} dims)")
            return True
        else:
            print("❌ No items with embeddings found")
            return False
            
    except Exception as e:
        print(f"❌ Table access error: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("🚀 RAG Semantic Search Test\n")
    
    tests = [
        ("Knowledge Table", test_knowledge_table),
        ("Semantic Search Direct", test_semantic_search_direct),
        ("RAG Service Search", test_rag_service_search)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*50)
    print("📊 RAG Test Results:")
    print("="*50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 RAG system is working!")
    else:
        print("⚠️ Some RAG components failed")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())
