#!/usr/bin/env python3
"""
Simple test for Ytili AI Agent core components
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_openrouter_client():
    """Test OpenRouter client"""
    print("🔧 Testing OpenRouter Client...")
    
    try:
        from app.ai_agent.openrouter_client import openrouter_client
        
        # Test health check
        result = await openrouter_client.health_check()
        print(f"  Health Check: {result.get('status', 'unknown')}")
        
        # Test simple completion
        test_messages = [{"role": "user", "content": "Hello"}]
        result = await openrouter_client.chat_completion(test_messages, max_tokens=20)
        
        if result.get("success"):
            print("  ✅ OpenRouter Client: Working")
            return True
        else:
            print(f"  ❌ OpenRouter Client: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ OpenRouter Client: {str(e)}")
        return False

async def test_emergency_handler():
    """Test Emergency Handler"""
    print("🚨 Testing Emergency Handler...")

    try:
        from app.ai_agent.emergency_handler import emergency_handler
        import uuid

        # Test emergency analysis with proper UUID
        test_user_id = str(uuid.uuid4())
        result = await emergency_handler.process_emergency_request(
            user_id=test_user_id,
            session_id="test_session",
            initial_message="Đau ngực, khó thở",
            location="Hà Nội"
        )
        
        if result.get("success"):
            print(f"  ✅ Emergency Handler: Priority {result.get('priority', 'unknown')}")
            return True
        else:
            print(f"  ❌ Emergency Handler: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Emergency Handler: {str(e)}")
        return False

async def test_fraud_detector():
    """Test Fraud Detector"""
    print("🔍 Testing Fraud Detector...")

    try:
        from app.ai_agent.fraud_detector import fraud_detector
        import uuid

        # Test campaign analysis with proper UUIDs
        test_campaign = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "title": "Hỗ trợ điều trị",
            "description": "Cần hỗ trợ chi phí điều trị tại bệnh viện",
            "goal_amount": 10000000
        }
        
        result = await fraud_detector.analyze_campaign(test_campaign)
        
        if "fraud_score" in result:
            print(f"  ✅ Fraud Detector: Score {result['fraud_score']}, Risk {result.get('risk_level', 'unknown')}")
            return True
        else:
            print(f"  ❌ Fraud Detector: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Fraud Detector: {str(e)}")
        return False

async def test_blockchain_integration():
    """Test Blockchain Integration"""
    print("⛓️  Testing Blockchain Integration...")
    
    try:
        from app.core.blockchain import blockchain_service
        
        # Test if blockchain service is initialized
        if blockchain_service.donation_registry is not None:
            print("  ✅ Blockchain: Service initialized")
            return True
        else:
            print("  ⚠️  Blockchain: Service initialized but contracts not loaded")
            return False
            
    except Exception as e:
        print(f"  ❌ Blockchain: {str(e)}")
        return False

async def test_database_connection():
    """Test Database Connection"""
    print("🗄️  Testing Database Connection...")
    
    try:
        from app.core.supabase import get_supabase_service
        
        supabase = get_supabase_service()
        
        # Test simple query
        result = supabase.table("users").select("id").limit(1).execute()
        
        if result.data is not None:
            print("  ✅ Database: Connection working")
            return True
        else:
            print("  ❌ Database: No data returned")
            return False
            
    except Exception as e:
        print(f"  ❌ Database: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Ytili AI Agent - Quick Health Check")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Blockchain Integration", test_blockchain_integration),
        ("OpenRouter Client", test_openrouter_client),
        ("Emergency Handler", test_emergency_handler),
        ("Fraud Detector", test_fraud_detector),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"  ❌ {test_name}: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    success_rate = (passed / total) * 100
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 AI Agent core components are working well!")
    else:
        print("⚠️  Some components need attention")
    
    return success_rate

if __name__ == "__main__":
    asyncio.run(main())
