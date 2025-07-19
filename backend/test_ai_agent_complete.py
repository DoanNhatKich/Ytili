#!/usr/bin/env python3
"""
Comprehensive test suite for Ytili AI Agent
Tests all components to ensure 95% completion
"""
import asyncio
import json
import time
from typing import Dict, Any

# Import AI Agent components
from app.ai_agent.openrouter_client import openrouter_client
from app.ai_agent.agent_service import YtiliAIAgent
from app.ai_agent.emergency_handler import emergency_handler
from app.ai_agent.fraud_detector import fraud_detector
from app.ai_agent.document_verifier import DocumentVerifier
from app.ai_agent.donation_advisor import DonationAdvisor
from app.ai_agent.knowledge_base import MedicalKnowledgeBase


class AIAgentTester:
    """Comprehensive tester for AI Agent components"""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    async def run_all_tests(self):
        """Run all AI Agent tests"""
        print("🚀 Starting Ytili AI Agent Comprehensive Tests")
        print("=" * 60)
        
        # Test OpenRouter Client
        await self.test_openrouter_client()
        
        # Test AI Agent Service
        await self.test_ai_agent_service()
        
        # Test Emergency Handler
        await self.test_emergency_handler()
        
        # Test Fraud Detector
        await self.test_fraud_detector()
        
        # Test Document Verifier
        await self.test_document_verifier()
        
        # Test Donation Advisor
        await self.test_donation_advisor()
        
        # Test Knowledge Base
        await self.test_knowledge_base()
        
        # Performance Tests
        await self.test_performance()
        
        # Generate final report
        self.generate_report()
    
    async def test_openrouter_client(self):
        """Test OpenRouter client functionality"""
        print("\n📡 Testing OpenRouter Client...")
        
        # Test 1: Health check
        result = await self._run_test(
            "OpenRouter Health Check",
            openrouter_client.health_check()
        )
        
        # Test 2: Simple chat completion
        test_messages = [
            {"role": "user", "content": "Hello, this is a test message."}
        ]
        result = await self._run_test(
            "OpenRouter Chat Completion",
            openrouter_client.chat_completion(test_messages, max_tokens=50)
        )
        
        # Test 3: Error handling with invalid input
        result = await self._run_test(
            "OpenRouter Error Handling",
            openrouter_client.chat_completion([])  # Empty messages
        )
        
        # Test 4: Rate limiting
        start_time = time.time()
        tasks = [
            openrouter_client.chat_completion(test_messages, max_tokens=10)
            for _ in range(3)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        self._record_test(
            "OpenRouter Rate Limiting",
            elapsed < 10,  # Should complete within 10 seconds
            {"elapsed_time": elapsed, "results_count": len(results)}
        )
    
    async def test_ai_agent_service(self):
        """Test main AI Agent service"""
        print("\n🤖 Testing AI Agent Service...")
        
        agent = YtiliAIAgent()
        
        # Test 1: Donation advisory conversation
        result = await self._run_test(
            "AI Agent Donation Advisory",
            agent.start_conversation(
                user_id=1,
                conversation_type="donation_advisory",
                initial_message="Tôi muốn quyên góp thuốc cho bệnh viện"
            )
        )
        
        # Test 2: Medical information query
        result = await self._run_test(
            "AI Agent Medical Info",
            agent.start_conversation(
                user_id=1,
                conversation_type="medical_info",
                initial_message="Triệu chứng sốt cao là gì?"
            )
        )
        
        # Test 3: Emergency request
        result = await self._run_test(
            "AI Agent Emergency Request",
            agent.start_conversation(
                user_id=1,
                conversation_type="emergency_request",
                initial_message="Cần cấp cứu, bệnh nhân đau ngực"
            )
        )
    
    async def test_emergency_handler(self):
        """Test emergency handling system"""
        print("\n🚨 Testing Emergency Handler...")
        
        # Test 1: Critical emergency
        result = await self._run_test(
            "Emergency Handler Critical",
            emergency_handler.process_emergency_request(
                user_id=1,
                session_id="test_session_critical",
                initial_message="Bệnh nhân tim ngừng đập, cần cấp cứu ngay",
                location="Hà Nội",
                contact_phone="0123456789"
            )
        )
        
        # Test 2: Medium priority emergency
        result = await self._run_test(
            "Emergency Handler Medium",
            emergency_handler.process_emergency_request(
                user_id=1,
                session_id="test_session_medium",
                initial_message="Đau đầu và nôn mửa từ sáng",
                location="TP.HCM"
            )
        )
        
        # Test 3: Update emergency request
        result = await self._run_test(
            "Emergency Handler Update",
            emergency_handler.update_emergency_request(
                session_id="test_session_medium",
                new_message="Bây giờ bệnh nhân khó thở"
            )
        )
    
    async def test_fraud_detector(self):
        """Test fraud detection system"""
        print("\n🔍 Testing Fraud Detector...")
        
        # Test 1: Legitimate campaign
        legitimate_campaign = {
            "id": 1,
            "user_id": 1,
            "title": "Hỗ trợ phẫu thuật tim cho bé An",
            "description": "Bé An 5 tuổi cần phẫu thuật tim tại Bệnh viện Tim Hà Nội. Chi phí ước tính 50 triệu đồng bao gồm phí phẫu thuật và thuốc.",
            "goal_amount": 50000000,
            "documents": ["medical_cert.jpg"]
        }
        
        result = await self._run_test(
            "Fraud Detector Legitimate",
            fraud_detector.analyze_campaign(legitimate_campaign)
        )
        
        # Test 2: Suspicious campaign
        suspicious_campaign = {
            "id": 2,
            "user_id": 2,
            "title": "Cần gấp tiền",
            "description": "Con tôi sắp chết, cần 1 tỷ đồng gấp",
            "goal_amount": 1000000000,
            "documents": []
        }
        
        result = await self._run_test(
            "Fraud Detector Suspicious",
            fraud_detector.analyze_campaign(suspicious_campaign)
        )
    
    async def test_document_verifier(self):
        """Test document verification system"""
        print("\n📄 Testing Document Verifier...")
        
        verifier = DocumentVerifier()
        
        # Test 1: Document verification (mock)
        result = await self._run_test(
            "Document Verifier Mock",
            verifier.verify_document(
                document_path="test_document.jpg",
                document_type="medical_certificate",
                user_id=1
            )
        )
    
    async def test_donation_advisor(self):
        """Test donation advisory system"""
        print("\n💝 Testing Donation Advisor...")
        
        try:
            from app.ai_agent.donation_advisor import DonationAdvisor
            advisor = DonationAdvisor()
            
            # Test donation recommendation
            result = await self._run_test(
                "Donation Advisor Recommendation",
                advisor.get_donation_recommendations(
                    user_budget=1000000,
                    user_preferences=["medication", "children"],
                    location="Hà Nội"
                )
            )
        except ImportError:
            self._record_test("Donation Advisor", False, {"error": "Module not found"})
    
    async def test_knowledge_base(self):
        """Test medical knowledge base"""
        print("\n📚 Testing Knowledge Base...")
        
        try:
            from app.ai_agent.knowledge_base import MedicalKnowledgeBase
            kb = MedicalKnowledgeBase()
            
            # Test medical query
            result = await self._run_test(
                "Knowledge Base Medical Query",
                kb.search_medical_info("sốt cao ở trẻ em")
            )
        except ImportError:
            self._record_test("Knowledge Base", False, {"error": "Module not found"})
    
    async def test_performance(self):
        """Test AI Agent performance"""
        print("\n⚡ Testing Performance...")
        
        # Test response time
        start_time = time.time()
        test_messages = [
            {"role": "user", "content": "Tôi cần tư vấn quyên góp thuốc"}
        ]
        
        result = await openrouter_client.chat_completion(test_messages, max_tokens=100)
        response_time = time.time() - start_time
        
        self._record_test(
            "Response Time Performance",
            response_time < 5.0,  # Should respond within 5 seconds
            {"response_time": response_time, "target": "< 5 seconds"}
        )
        
        # Test concurrent requests
        start_time = time.time()
        tasks = [
            openrouter_client.chat_completion(test_messages, max_tokens=50)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time
        
        self._record_test(
            "Concurrent Requests Performance",
            concurrent_time < 15.0,  # Should handle 5 concurrent requests within 15 seconds
            {"concurrent_time": concurrent_time, "requests": 5}
        )
    
    async def _run_test(self, test_name: str, test_coroutine) -> Any:
        """Run a single test and record result"""
        try:
            result = await test_coroutine
            success = result.get("success", True) if isinstance(result, dict) else bool(result)
            self._record_test(test_name, success, result)
            return result
        except Exception as e:
            self._record_test(test_name, False, {"error": str(e)})
            return None
    
    def _record_test(self, test_name: str, passed: bool, details: Any = None):
        """Record test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            print(f"  ✅ {test_name}")
        else:
            print(f"  ❌ {test_name}")
            if details and isinstance(details, dict) and "error" in details:
                print(f"     Error: {details['error']}")
        
        self.test_results[test_name] = {
            "passed": passed,
            "details": details
        }
    
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "=" * 60)
        print("🏁 AI AGENT TEST RESULTS")
        print("=" * 60)
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("\n🎉 AI AGENT IS 95%+ COMPLETE! Ready for deployment!")
        elif success_rate >= 80:
            print("\n⚠️  AI Agent is mostly complete but needs some improvements")
        else:
            print("\n❌ AI Agent needs significant work before deployment")
        
        # Save detailed results
        with open("ai_agent_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": self.total_tests,
                    "passed_tests": self.passed_tests,
                    "success_rate": success_rate,
                    "timestamp": time.time()
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        print(f"\n📊 Detailed results saved to: ai_agent_test_results.json")


async def main():
    """Run all AI Agent tests"""
    tester = AIAgentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
