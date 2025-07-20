#!/usr/bin/env python3
"""
Test script to verify OpenRouter API connection and RAG integration
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.ai_agent.openrouter_client import openrouter_client
from app.ai_agent.agent_service import ytili_ai_agent
from app.ai_agent.rag_service import rag_service
from app.models.ai_agent import ConversationType
from app.core.config import settings


async def test_openrouter_connection():
    """Test OpenRouter API connection with new API key and model"""
    print("🔧 Testing OpenRouter API Connection...")
    print(f"API Key: {settings.OPENROUTER_API_KEY[:20]}...")
    print(f"Primary Model: {settings.PRIMARY_MODEL}")
    print(f"Base URL: {settings.OPENROUTER_BASE_URL}")
    
    # Test health check
    health_result = await openrouter_client.health_check()
    print(f"Health Check: {health_result}")
    
    if health_result["status"] == "healthy":
        print("✅ OpenRouter connection successful!")
        return True
    else:
        print(f"❌ OpenRouter connection failed: {health_result.get('error')}")
        return False


async def test_basic_chat():
    """Test basic chat completion"""
    print("\n🤖 Testing Basic Chat Completion...")
    
    test_messages = [
        {"role": "user", "content": "Xin chào! Bạn có thể giúp tôi hiểu về cảm cúm không?"}
    ]
    
    result = await openrouter_client.chat_completion(test_messages)
    
    if result["success"]:
        print("✅ Chat completion successful!")
        print(f"Model used: {result['model_used']}")
        print(f"Response time: {result['response_time']:.2f}s")
        print(f"Response: {result['response'][:200]}...")
        return True
    else:
        print(f"❌ Chat completion failed: {result['error']}")
        return False


async def test_rag_service():
    """Test RAG service functionality"""
    print("\n📚 Testing RAG Service...")
    
    # Test embedding generation
    test_text = "Triệu chứng cảm cúm"
    embedding = await rag_service.get_embedding(test_text)
    
    if embedding:
        print(f"✅ Embedding generated successfully! Dimension: {len(embedding)}")
    else:
        print("❌ Failed to generate embedding")
        return False
    
    # Test knowledge search
    search_results = await rag_service.search_knowledge(
        query="cảm cúm sốt",
        content_type="medical_info",
        limit=3
    )
    
    print(f"Knowledge search results: {len(search_results)} items found")
    for i, result in enumerate(search_results):
        print(f"  {i+1}. {result.get('title', 'No title')} (score: {result.get('similarity_score', 0):.3f})")
    
    return len(search_results) > 0


async def test_ai_agent_conversation():
    """Test full AI agent conversation with RAG"""
    print("\n🎯 Testing AI Agent Conversation with RAG...")

    # Get an existing user with auth_user_id
    from app.core.supabase import get_supabase_service
    supabase = get_supabase_service()

    users_result = supabase.table("users").select("auth_user_id").not_.is_("auth_user_id", "null").limit(1).execute()

    if not users_result.data:
        print("❌ No users with auth_user_id found")
        return False

    user_id = users_result.data[0]['auth_user_id']
    print(f"Using user ID: {user_id}")

    # Start a conversation
    conversation_result = await ytili_ai_agent.start_conversation(
        user_id=user_id,
        conversation_type=ConversationType.MEDICAL_INFO,
        initial_message="Tôi bị sốt và ho, có phải cảm cúm không?"
    )
    
    if not conversation_result["success"]:
        print(f"❌ Failed to start conversation: {conversation_result['error']}")
        return False
    
    print(f"✅ Conversation started: {conversation_result['session_id']}")
    
    # Send a message
    message_result = await ytili_ai_agent.send_message(
        session_id=conversation_result["session_id"],
        user_message="Tôi nên làm gì để điều trị?"
    )
    
    if message_result["success"]:
        print("✅ Message sent and response received!")
        print(f"Model used: {message_result['model_used']}")
        print(f"Response time: {message_result['response_time']:.2f}s")
        print(f"Response: {message_result['response'][:300]}...")
        return True
    else:
        print(f"❌ Failed to send message: {message_result['error']}")
        return False


async def test_blockchain_integration():
    """Test blockchain integration"""
    print("\n⛓️ Testing Blockchain Integration...")
    
    try:
        from app.core.blockchain import blockchain_service
        
        # Test connection
        if blockchain_service.w3.is_connected():
            print("✅ Blockchain connection successful!")
            
            # Test account
            print(f"Account address: {blockchain_service.account.address}")
            
            # Test balance (if possible)
            try:
                balance = blockchain_service.w3.eth.get_balance(blockchain_service.account.address)
                print(f"Account balance: {blockchain_service.w3.from_wei(balance, 'ether')} ETH")
            except Exception as e:
                print(f"⚠️ Could not get balance: {e}")
            
            return True
        else:
            print("❌ Blockchain connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Blockchain test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Ytili AI Agent Integration Tests\n")
    
    tests = [
        ("OpenRouter Connection", test_openrouter_connection),
        ("Basic Chat", test_basic_chat),
        ("RAG Service", test_rag_service),
        ("AI Agent Conversation", test_ai_agent_conversation),
        ("Blockchain Integration", test_blockchain_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
        
        print()  # Add spacing between tests
    
    # Summary
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ytili AI Agent is ready!")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())
