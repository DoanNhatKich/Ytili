#!/usr/bin/env python3
"""Debug script for RAG system issues"""

import asyncio
import sys
import os
import numpy as np

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.supabase import get_supabase_service
from app.ai_agent.rag_service import rag_service

async def debug_rag_system():
    """Debug RAG search issues"""
    print("🔍 Debugging RAG System...")
    
    # Initialize services
    supabase = get_supabase_service()

    print("✅ RAG service initialized")
    
    # 1. Check knowledge base data
    print("\n📚 Checking knowledge base...")
    try:
        result = supabase.table("rag_knowledge_base").select("id, title, embedding, is_verified").limit(10).execute()
        
        print(f"Total knowledge items: {len(result.data)}")
        for item in result.data:
            has_embedding = item.get('embedding') is not None
            is_verified = item.get('is_verified', False)
            print(f"ID: {item['id']}, Title: {item['title'][:50]}..., Has Embedding: {has_embedding}, Verified: {is_verified}")
    except Exception as e:
        print(f"❌ Failed to check knowledge base: {e}")
        return
    
    # 2. Test embedding generation
    print("\n🧠 Testing embedding generation...")
    test_query = "triệu chứng cảm cúm"
    try:
        embedding = await rag_service.get_embedding(test_query)
        if embedding:
            print(f"✅ Query: {test_query}")
            print(f"✅ Embedding dimension: {len(embedding)}")
            print(f"✅ Embedding sample: {embedding[:5]}...")
        else:
            print("❌ Failed to generate embedding")
            return
    except Exception as e:
        print(f"❌ Embedding generation error: {e}")
        return
    
    # 3. Test direct SQL search with different thresholds
    print("\n🔍 Testing SQL search with different thresholds...")
    
    thresholds = [0.1, 0.3, 0.5, 0.7]
    
    for threshold in thresholds:
        print(f"\n--- Testing threshold: {threshold} ---")
        try:
            result = supabase.rpc('search_knowledge_semantic', {
                'query_embedding': embedding,
                'content_type_filter': 'medical_info',
                'limit_results': 5,
                'similarity_threshold': threshold
            }).execute()
            
            print(f"Results with threshold {threshold}: {len(result.data)} items")
            for item in result.data:
                print(f"  - {item.get('title', 'No title')[:40]}...: {item.get('similarity_score', 0):.3f}")
                
        except Exception as e:
            print(f"❌ Search error with threshold {threshold}: {e}")
    
    # 4. Test keyword fallback
    print("\n🔤 Testing keyword fallback search...")
    try:
        result = supabase.table("rag_knowledge_base").select("id, title, content").eq("is_verified", True).text_search("content", test_query).limit(3).execute()
        
        print(f"Keyword search results: {len(result.data)} items")
        for item in result.data:
            print(f"  - {item.get('title', 'No title')[:40]}...")
            
    except Exception as e:
        print(f"❌ Keyword search error: {e}")
    
    # 5. Check user table structure
    print("\n👤 Checking user tables...")
    
    # Check auth.users
    try:
        auth_result = supabase.table("auth.users").select("id, email").limit(1).execute()
        print(f"auth.users table: {len(auth_result.data)} users found")
    except Exception as e:
        print(f"❌ Cannot access auth.users: {e}")
    
    # Check users table
    try:
        users_result = supabase.table("users").select("id, email, auth_user_id").limit(5).execute()
        print(f"users table: {len(users_result.data)} users found")
        for user in users_result.data:
            print(f"  - ID: {user.get('id')}, Email: {user.get('email')}, Auth ID: {user.get('auth_user_id')}")
    except Exception as e:
        print(f"❌ Cannot access users table: {e}")
    
    # Check test user specifically
    test_user_id = "550e8400-e29b-41d4-a716-446655440000"
    print(f"\n🔍 Checking test user: {test_user_id}")
    
    try:
        # Check in auth.users
        auth_user = supabase.table("auth.users").select("*").eq("id", test_user_id).execute()
        print(f"Test user in auth.users: {len(auth_user.data)} found")
        
        # Check in users table
        user_record = supabase.table("users").select("*").eq("auth_user_id", test_user_id).execute()
        print(f"Test user in users table: {len(user_record.data)} found")
        
    except Exception as e:
        print(f"❌ Error checking test user: {e}")

if __name__ == "__main__":
    asyncio.run(debug_rag_system())
