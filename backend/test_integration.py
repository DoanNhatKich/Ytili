#!/usr/bin/env python3
"""
Integration test script for Ytili platform
Tests the complete flow: Supabase Auth -> VietQR Payment -> Blockchain Recording -> Token Rewards
"""
import asyncio
import json
import httpx
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_USER = {
    "email": "test@ytili.com",
    "password": "TestPassword123!",
    "full_name": "Test User",
    "user_type": "individual",
    "phone": "+84901234567",
    "city": "Ho Chi Minh City",
    "province": "Ho Chi Minh",
    "country": "Vietnam"
}

class YtiliIntegrationTest:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL)
        self.access_token = None
        self.user_id = None
        self.donation_id = None
        self.payment_reference = None
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def print_step(self, step: str, status: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{status}] {step}")
    
    def print_result(self, data: dict):
        print(f"   └─ {json.dumps(data, indent=6)}")
    
    async def test_supabase_auth(self):
        """Test Supabase authentication system"""
        self.print_step("Testing Supabase Authentication", "TEST")
        
        # 1. Register user
        self.print_step("Registering new user...")
        try:
            response = await self.client.post("/supabase-auth/register", json=TEST_USER)
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ User registration successful", "SUCCESS")
                self.print_result(result)
            else:
                self.print_step(f"❌ Registration failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Registration error: {e}", "ERROR")
            return False
        
        # 2. Login user
        self.print_step("Logging in user...")
        try:
            login_data = {"email": TEST_USER["email"], "password": TEST_USER["password"]}
            response = await self.client.post("/supabase-auth/login", json=login_data)
            if response.status_code == 200:
                result = response.json()
                self.access_token = result["access_token"]
                self.user_id = result["user"]["id"]
                self.print_step("✅ User login successful", "SUCCESS")
                self.print_result({"access_token": self.access_token[:20] + "...", "user_id": self.user_id})
            else:
                self.print_step(f"❌ Login failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Login error: {e}", "ERROR")
            return False
        
        # 3. Get user profile
        self.print_step("Getting user profile...")
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await self.client.get("/supabase-auth/me", headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Profile retrieval successful", "SUCCESS")
                self.print_result(result["user"])
            else:
                self.print_step(f"❌ Profile retrieval failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Profile error: {e}", "ERROR")
            return False
        
        return True
    
    async def test_donation_creation(self):
        """Test donation creation"""
        self.print_step("Testing Donation Creation", "TEST")
        
        donation_data = {
            "title": "Emergency Medical Supplies",
            "description": "Bandages and first aid supplies for local hospital",
            "donation_type": "medical_supply",
            "item_name": "Medical Bandages",
            "quantity": 100,
            "unit": "pieces",
            "amount": 1000000,  # 1M VND
            "pickup_address": "123 Test Street, Ho Chi Minh City",
            "notes": "Integration test donation"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await self.client.post("/donations", json=donation_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.donation_id = result["id"]
                self.print_step("✅ Donation creation successful", "SUCCESS")
                self.print_result({"donation_id": self.donation_id})
                return True
            else:
                self.print_step(f"❌ Donation creation failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Donation creation error: {e}", "ERROR")
            return False
    
    async def test_vietqr_payment(self):
        """Test VietQR payment system"""
        self.print_step("Testing VietQR Payment System", "TEST")
        
        # 1. Create payment QR
        self.print_step("Creating VietQR payment...")
        payment_data = {
            "donation_id": self.donation_id,
            "amount": 1000000,
            "description": "Payment for medical supplies donation",
            "expires_in_minutes": 30
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await self.client.post("/vietqr-payments/create-qr", json=payment_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.payment_reference = result["data"]["payment_reference"]
                self.print_step("✅ VietQR payment creation successful", "SUCCESS")
                self.print_result({
                    "payment_reference": self.payment_reference,
                    "qr_code_length": len(result["data"]["qr_code"]),
                    "amount": result["data"]["amount"],
                    "expires_at": result["data"]["expires_at"]
                })
            else:
                self.print_step(f"❌ VietQR payment creation failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ VietQR payment error: {e}", "ERROR")
            return False
        
        # 2. Simulate payment verification
        self.print_step("Simulating payment verification...")
        verification_data = {
            "payment_reference": self.payment_reference,
            "bank_transaction_id": f"BANK_TX_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        try:
            response = await self.client.post("/vietqr-payments/verify", json=verification_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Payment verification successful", "SUCCESS")
                self.print_result(result["data"])
                return True
            else:
                self.print_step(f"❌ Payment verification failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Payment verification error: {e}", "ERROR")
            return False
    
    async def test_blockchain_integration(self):
        """Test blockchain integration"""
        self.print_step("Testing Blockchain Integration", "TEST")
        
        # 1. Get transparency data
        self.print_step("Getting transparency data...")
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await self.client.get(f"/blockchain/transparency/{self.donation_id}", headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Transparency data retrieval successful", "SUCCESS")
                self.print_result(result)
            else:
                self.print_step(f"❌ Transparency data failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Transparency data error: {e}", "ERROR")
            return False
        
        # 2. Get contract information
        self.print_step("Getting contract information...")
        try:
            response = await self.client.get("/blockchain/contracts/info")
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Contract info retrieval successful", "SUCCESS")
                self.print_result(result)
                return True
            else:
                self.print_step(f"❌ Contract info failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Contract info error: {e}", "ERROR")
            return False
    
    async def test_token_system(self):
        """Test token reward system"""
        self.print_step("Testing Token Reward System", "TEST")
        
        # 1. Get token balance
        self.print_step("Getting token balance...")
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await self.client.get("/tokens/balance", headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Token balance retrieval successful", "SUCCESS")
                self.print_result(result)
            else:
                self.print_step(f"❌ Token balance failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Token balance error: {e}", "ERROR")
            return False
        
        # 2. Get redemption options
        self.print_step("Getting redemption options...")
        try:
            response = await self.client.get("/tokens/redemption-options")
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Redemption options retrieval successful", "SUCCESS")
                self.print_result({"options_count": len(result), "first_option": result[0] if result else None})
            else:
                self.print_step(f"❌ Redemption options failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Redemption options error: {e}", "ERROR")
            return False
        
        # 3. Get contract info
        self.print_step("Getting token contract info...")
        try:
            response = await self.client.get("/tokens/contract/info")
            if response.status_code == 200:
                result = response.json()
                self.print_step("✅ Token contract info retrieval successful", "SUCCESS")
                self.print_result(result)
                return True
            else:
                self.print_step(f"❌ Token contract info failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.print_step(f"❌ Token contract info error: {e}", "ERROR")
            return False
    
    async def run_full_test(self):
        """Run complete integration test"""
        self.print_step("🚀 Starting Ytili Platform Integration Test", "START")
        print("=" * 80)
        
        tests = [
            ("Supabase Authentication", self.test_supabase_auth),
            ("Donation Creation", self.test_donation_creation),
            ("VietQR Payment", self.test_vietqr_payment),
            ("Blockchain Integration", self.test_blockchain_integration),
            ("Token System", self.test_token_system)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'-' * 60}")
            try:
                if await test_func():
                    passed += 1
                    self.print_step(f"✅ {test_name} PASSED", "PASS")
                else:
                    self.print_step(f"❌ {test_name} FAILED", "FAIL")
            except Exception as e:
                self.print_step(f"❌ {test_name} ERROR: {e}", "ERROR")
        
        print(f"\n{'=' * 80}")
        self.print_step(f"🏁 Integration Test Complete: {passed}/{total} tests passed", "FINAL")
        
        if passed == total:
            self.print_step("🎉 ALL TESTS PASSED! Ytili platform is working correctly.", "SUCCESS")
            return True
        else:
            self.print_step(f"⚠️  {total - passed} tests failed. Please check the logs above.", "WARNING")
            return False


async def main():
    """Main test function"""
    print("Ytili Platform Integration Test")
    print("=" * 80)
    print("This script tests the complete Ytili platform integration:")
    print("• Supabase Authentication")
    print("• VietQR Payment System")
    print("• Saga Blockchain Integration")
    print("• YTILI Token Rewards")
    print("=" * 80)
    
    async with YtiliIntegrationTest() as test:
        success = await test.run_full_test()
        
        if success:
            print("\n🎯 Next steps:")
            print("1. Deploy to production environment")
            print("2. Configure real VietQR API credentials")
            print("3. Set up monitoring and logging")
            print("4. Run load testing")
            exit(0)
        else:
            print("\n🔧 Fix the failing tests before proceeding to production.")
            exit(1)


if __name__ == "__main__":
    asyncio.run(main())
