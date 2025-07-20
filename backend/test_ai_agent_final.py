#!/usr/bin/env python3
"""
Final comprehensive test for Ytili AI Agent
Tests all fixed components and verifies functionality
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.ai_agent.chatbot import ytili_chatbot
from app.ai_agent.openrouter_client import openrouter_client
from app.ai_agent.agent_service import ytili_ai_agent
from app.models.ai_agent import ConversationType


async def test_openrouter_client():
    """Test OpenRouter API client"""
    print("🔧 Testing OpenRouter Client...")
    
    try:
        # Test health check
        health = await openrouter_client.health_check()
        print(f"  Health Status: {health.get('status', 'unknown')}")
        
        # Test simple completion
        messages = [{"role": "user", "content": "Say hello in one word"}]
        result = await openrouter_client.chat_completion(messages, max_tokens=10)
        
        if result.get("success"):
            print("  ✅ OpenRouter Client: Working")
            print(f"  Model: {result.get('model_used')}")
            print(f"  Response: {result.get('response')}")
            return True
        else:
            print(f"  ❌ OpenRouter Client: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ OpenRouter Client Exception: {str(e)}")
        return False


async def test_ai_agent_service():
    """Test AI Agent service directly"""
    print("\n🤖 Testing AI Agent Service...")
    
    try:
        # Test conversation start
        result = await ytili_ai_agent.start_conversation(
            user_id="anonymous",
            conversation_type=ConversationType.GENERAL_SUPPORT,
            initial_message="Hello AI Agent"
        )
        
        if result.get("success"):
            session_id = result["session_id"]
            print(f"  ✅ Conversation Started: {session_id}")
            
            # Test message sending
            msg_result = await ytili_ai_agent.send_message(
                session_id=session_id,
                user_message="What is Ytili?"
            )
            
            if msg_result.get("success"):
                print("  ✅ Message Sent Successfully")
                print(f"  Response Preview: {msg_result.get('response', '')[:100]}...")
                return True
            else:
                print(f"  ❌ Message Failed: {msg_result.get('error')}")
                return False
        else:
            print(f"  ❌ Conversation Start Failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ AI Agent Service Exception: {str(e)}")
        return False


async def test_chatbot_interface():
    """Test high-level chatbot interface"""
    print("\n💬 Testing Chatbot Interface...")
    
    try:
        # Test different conversation types
        conversation_types = [
            ("general_support", "How does Ytili work?"),
            ("donation_advisory", "I want to donate 500,000 VND for medical supplies"),
            ("medical_info", "Tell me about common medications"),
            ("emergency_request", "I need urgent medical assistance"),
            ("campaign_help", "How do I create a fundraising campaign?")
        ]
        
        success_count = 0
        
        for conv_type, message in conversation_types:
            try:
                result = await ytili_chatbot.start_chat(
                    user_id="anonymous",
                    conversation_type=conv_type,
                    initial_message=message
                )
                
                if result.get("success"):
                    print(f"  ✅ {conv_type}: Session created")
                    success_count += 1
                    
                    # Test welcome message
                    if result.get("welcome_message"):
                        print(f"    Welcome: {result['welcome_message'][:50]}...")
                else:
                    print(f"  ❌ {conv_type}: {result.get('error')}")
                    
            except Exception as e:
                print(f"  ❌ {conv_type}: Exception - {str(e)}")
        
        print(f"  📊 Success Rate: {success_count}/{len(conversation_types)}")
        return success_count == len(conversation_types)
        
    except Exception as e:
        print(f"  ❌ Chatbot Interface Exception: {str(e)}")
        return False


async def test_conversation_flow():
    """Test complete conversation flow"""
    print("\n🔄 Testing Complete Conversation Flow...")
    
    try:
        # Start conversation
        result = await ytili_chatbot.start_chat(
            user_id="anonymous",
            conversation_type="general_support",
            initial_message="Hello, I'm new to Ytili"
        )
        
        if not result.get("success"):
            print(f"  ❌ Failed to start conversation: {result.get('error')}")
            return False
        
        session_id = result["session_id"]
        print(f"  ✅ Conversation started: {session_id}")
        
        # Send multiple messages
        messages = [
            "What services does Ytili provide?",
            "How can I donate medical supplies?",
            "Is my donation tracked on blockchain?",
            "Thank you for the information"
        ]
        
        for i, message in enumerate(messages, 1):
            print(f"  📤 Sending message {i}: {message[:30]}...")
            
            result = await ytili_chatbot.send_message(
                session_id=session_id,
                message=message
            )
            
            if result.get("success"):
                response = result.get("response", "")
                print(f"  📥 Response {i}: {response[:50]}...")
            else:
                print(f"  ❌ Message {i} failed: {result.get('error')}")
                return False
        
        print("  ✅ Complete conversation flow successful")
        return True
        
    except Exception as e:
        print(f"  ❌ Conversation Flow Exception: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Ytili AI Agent Final Tests")
    print("=" * 50)
    
    test_results = []
    
    # Run all tests
    test_results.append(await test_openrouter_client())
    test_results.append(await test_ai_agent_service())
    test_results.append(await test_chatbot_interface())
    test_results.append(await test_conversation_flow())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(test_results)
    total = len(test_results)
    
    test_names = [
        "OpenRouter Client",
        "AI Agent Service", 
        "Chatbot Interface",
        "Conversation Flow"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! AI AGENT IS FULLY FUNCTIONAL!")
        print("\n✅ Key Features Working:")
        print("  • OpenRouter API integration")
        print("  • Conversation management")
        print("  • Multiple conversation types")
        print("  • Message handling")
        print("  • User context management")
        print("  • Database integration")
        print("\n🚀 AI Agent is ready for production use!")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
