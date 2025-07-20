#!/usr/bin/env python3
"""
Test individual components of Ytili AI Agent
"""
import asyncio
import sys
import os
import uuid

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.ai_agent.openrouter_client import openrouter_client
from app.ai_agent.rag_service import rag_service
from app.core.config import settings


async def test_openrouter_basic():
    """Test basic OpenRouter functionality"""
    print("🔧 Testing OpenRouter API...")
    print(f"API Key: {settings.OPENROUTER_API_KEY[:20]}...")
    print(f"Model: {settings.PRIMARY_MODEL}")
    
    try:
        # Simple test message
        messages = [{"role": "user", "content": "Hello, respond with just 'OK'"}]
        result = await openrouter_client.chat_completion(messages)
        
        if result["success"]:
            print("✅ OpenRouter API working")
            print(f"Response: {result['response']}")
            return True
        else:
            print(f"❌ OpenRouter failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ OpenRouter error: {str(e)}")
        return False


async def test_embeddings():
    """Test embedding generation"""
    print("\n📚 Testing Embedding Generation...")
    
    try:
        test_text = "Triệu chứng cảm cúm"
        embedding = await rag_service.get_embedding(test_text)
        
        if embedding and len(embedding) == 384:
            print(f"✅ Embedding generated: {len(embedding)} dimensions")
            return True
        else:
            print("❌ Embedding generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Embedding error: {str(e)}")
        return False


async def test_supabase_connection():
    """Test Supabase connection"""
    print("\n🗄️ Testing Supabase Connection...")
    
    try:
        from app.core.supabase import get_supabase_service
        supabase = get_supabase_service()
        
        # Try to access a simple table
        result = supabase.table('users').select('id').limit(1).execute()
        print("✅ Supabase connection working")
        return True
        
    except Exception as e:
        print(f"❌ Supabase error: {str(e)}")
        return False


async def test_rag_table():
    """Test RAG knowledge base table"""
    print("\n📋 Testing RAG Knowledge Base Table...")
    
    try:
        from app.core.supabase import get_supabase_service
        supabase = get_supabase_service()
        
        # Check if table exists
        result = supabase.table('rag_knowledge_base').select('id, title').limit(3).execute()
        
        if result.data:
            print(f"✅ RAG table exists with {len(result.data)} items")
            for item in result.data:
                print(f"  - {item.get('title', 'No title')}")
            return True
        else:
            print("⚠️ RAG table exists but is empty")
            return False
            
    except Exception as e:
        print(f"❌ RAG table error: {str(e)}")
        print("💡 Please run the SQL setup in Supabase first!")
        return False


async def test_ai_conversation():
    """Test AI conversation without RAG"""
    print("\n🤖 Testing AI Conversation (without RAG)...")
    
    try:
        # Simple conversation test
        messages = [
            {"role": "system", "content": "You are a helpful medical assistant. Keep responses brief."},
            {"role": "user", "content": "Tôi bị sốt nhẹ, nên làm gì?"}
        ]
        
        result = await openrouter_client.chat_completion(messages)
        
        if result["success"]:
            print("✅ AI conversation working")
            print(f"Response preview: {result['response'][:100]}...")
            return True
        else:
            print(f"❌ AI conversation failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ AI conversation error: {str(e)}")
        return False


async def test_blockchain():
    """Test blockchain connection"""
    print("\n⛓️ Testing Blockchain Connection...")
    
    try:
        from app.core.blockchain import blockchain_service
        
        if blockchain_service.w3.is_connected():
            print("✅ Blockchain connected")
            print(f"Account: {blockchain_service.account.address}")
            return True
        else:
            print("❌ Blockchain not connected")
            return False
            
    except Exception as e:
        print(f"❌ Blockchain error: {str(e)}")
        return False


async def main():
    """Run all component tests"""
    print("🚀 Ytili AI Agent Component Tests\n")
    
    tests = [
        ("OpenRouter API", test_openrouter_basic),
        ("Embeddings", test_embeddings),
        ("Supabase Connection", test_supabase_connection),
        ("RAG Knowledge Table", test_rag_table),
        ("AI Conversation", test_ai_conversation),
        ("Blockchain", test_blockchain)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*50)
    print("📊 Component Test Results:")
    print("="*50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"Total: {passed}/{total} components working")
    
    if passed >= 4:  # At least core components working
        print("🎉 Core components are ready!")
        
        if results.get("RAG Knowledge Table", False):
            print("\n🔄 Next step: Run 'python populate_embeddings.py' to generate embeddings")
        else:
            print("\n📋 Next step: Run the SQL setup in Supabase dashboard")
            print("   File: supabase_rag_setup.sql")
    else:
        print("⚠️ Critical components failed. Please fix the issues above.")
    
    return passed >= 4


if __name__ == "__main__":
    asyncio.run(main())
