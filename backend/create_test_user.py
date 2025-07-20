#!/usr/bin/env python3
"""Create test user for AI Agent testing"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.supabase import get_supabase_service

async def create_test_user():
    """Create test user for AI Agent testing or use existing user"""
    print("👤 Setting up test user for AI Agent...")

    supabase = get_supabase_service()

    try:
        # First, try to find an existing user with auth_user_id
        existing_users = supabase.table("users").select("*").not_.is_("auth_user_id", "null").limit(1).execute()

        if existing_users.data:
            user = existing_users.data[0]
            print(f"✅ Using existing user: {user['email']}")
            print(f"   User ID: {user['id']}")
            print(f"   Auth User ID: {user['auth_user_id']}")
            return user

        # If no users with auth_user_id, create a test user without auth_user_id
        print("No users with auth_user_id found. Creating test user without auth constraint...")

        test_user_data = {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "email": "aitest@ytili.com",
            "full_name": "AI Test User",
            "user_type": "individual",
            "status": "verified",
            "is_email_verified": True,
            "is_phone_verified": False,
            "is_kyc_verified": False,
            "phone": "+84987654321",
            "address": "123 Test Street",
            "city": "Ho Chi Minh City",
            "province": "Ho Chi Minh",
            "country": "Vietnam"
            # No auth_user_id to avoid foreign key constraint
        }

        # Check if this test user already exists
        existing_test_user = supabase.table("users").select("*").eq("email", test_user_data["email"]).execute()

        if existing_test_user.data:
            print(f"✅ Test user already exists: {existing_test_user.data[0]['email']}")
            return existing_test_user.data[0]

        # Create new test user
        result = supabase.table("users").insert(test_user_data).execute()

        if result.data:
            user = result.data[0]
            print(f"✅ Test user created successfully!")
            print(f"   Email: {user['email']}")
            print(f"   User ID: {user['id']}")

            # Create user points record
            points_data = {
                "user_id": user['id'],
                "total_points": 100,
                "available_points": 100,
                "lifetime_earned": 100,
                "lifetime_spent": 0,
                "tier_level": "Bronze"
            }

            try:
                points_result = supabase.table("user_points").insert(points_data).execute()
                if points_result.data:
                    print(f"✅ User points created: {points_result.data[0]['total_points']} points")
            except Exception as pe:
                print(f"⚠️ Could not create user points: {pe}")

            return user
        else:
            print("❌ Failed to create test user")
            return None

    except Exception as e:
        print(f"❌ Error setting up test user: {e}")
        return None

async def test_ai_conversation_with_test_user(user):
    """Test AI conversation with the test user"""
    print("\n🤖 Testing AI conversation with test user...")

    try:
        from app.ai_agent.agent_service import ytili_ai_agent
        from app.models.ai_agent import ConversationType

        # Use the user's auth_user_id if available, otherwise use a test ID
        user_id = user.get('auth_user_id') or "550e8400-e29b-41d4-a716-446655440000"

        print(f"Using user ID: {user_id}")

        # Start conversation
        conversation_result = await ytili_ai_agent.start_conversation(
            user_id=user_id,
            conversation_type=ConversationType.MEDICAL_INFO,
            initial_message="Xin chào! Tôi muốn hỏi về triệu chứng cảm cúm."
        )

        if conversation_result["success"]:
            print(f"✅ Conversation started: {conversation_result['session_id']}")

            # Send a follow-up message
            message_result = await ytili_ai_agent.send_message(
                session_id=conversation_result["session_id"],
                user_message="Tôi bị sốt 38 độ và ho khan. Tôi nên làm gì?"
            )

            if message_result["success"]:
                print("✅ Message sent successfully!")
                print(f"Model used: {message_result['model_used']}")
                print(f"Response time: {message_result['response_time']:.2f}s")
                print(f"Response preview: {message_result['response'][:200]}...")
                return True
            else:
                print(f"❌ Failed to send message: {message_result['error']}")
                return False
        else:
            print(f"❌ Failed to start conversation: {conversation_result['error']}")
            return False

    except Exception as e:
        print(f"❌ AI conversation test failed: {e}")
        return False

async def test_rag_search():
    """Test RAG search functionality"""
    print("\n📚 Testing RAG search...")
    
    try:
        from app.ai_agent.rag_service import rag_service
        
        test_queries = [
            "triệu chứng cảm cúm",
            "paracetamol liều dùng",
            "sơ cứu bỏng",
            "quyên góp thuốc an toàn"
        ]
        
        for query in test_queries:
            results = await rag_service.search_knowledge(
                query=query,
                limit=2
            )
            
            print(f"Query: '{query}' -> {len(results)} results")
            for result in results:
                score = result.get('similarity_score', 0)
                title = result.get('title', 'No title')[:40]
                print(f"  - {title}... (score: {score:.3f})")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG search test failed: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("🚀 Setting up test environment for Ytili AI Agent\n")
        
        # Create test user
        user = await create_test_user()
        
        if user:
            # Test RAG search
            rag_success = await test_rag_search()
            
            # Test AI conversation
            ai_success = await test_ai_conversation_with_test_user(user)
            
            print(f"\n📊 Test Results:")
            print(f"User Creation: ✅")
            print(f"RAG Search: {'✅' if rag_success else '❌'}")
            print(f"AI Conversation: {'✅' if ai_success else '❌'}")
            
            if rag_success and ai_success:
                print("\n🎉 All tests passed! AI Agent is ready for integration testing.")
            else:
                print("\n⚠️ Some tests failed. Please check the issues above.")
        else:
            print("\n❌ Failed to create test user. Cannot proceed with tests.")
    
    asyncio.run(main())
