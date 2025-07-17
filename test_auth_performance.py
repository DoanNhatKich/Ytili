#!/usr/bin/env python3
"""
Performance test script for Ytili authentication endpoints
Tests registration and login performance to ensure sub-3s targets
"""

import requests
import time
import json
import random
import string
from typing import Dict, Any


def generate_test_user() -> Dict[str, Any]:
    """Generate a random test user for registration"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    return {
        "email": f"test_{random_suffix}@example.com",
        "password": "TestPassword123!",
        "full_name": f"Test User {random_suffix}",
        "user_type": "individual",
        "phone": f"+84{random.randint(100000000, 999999999)}",
        "city": "Ho Chi Minh City",
        "province": "Ho Chi Minh",
        "country": "Vietnam"
    }


def test_registration_performance(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test user registration performance"""
    print("🧪 Testing Registration Performance...")
    
    user_data = generate_test_user()
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/register",
            json=user_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "success": response.status_code in [200, 201],
            "status_code": response.status_code,
            "duration": duration,
            "target_met": duration < 3.0,  # Target: under 3 seconds
            "user_email": user_data["email"]
        }
        
        if result["success"]:
            print(f"✅ Registration successful in {duration:.2f}s")
            result["response_data"] = response.json()
        else:
            print(f"❌ Registration failed: {response.status_code}")
            try:
                result["error"] = response.json()
            except:
                result["error"] = response.text
        
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Registration error after {duration:.2f}s: {e}")
        return {
            "success": False,
            "duration": duration,
            "target_met": False,
            "error": str(e)
        }


def test_login_performance(email: str, password: str, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test user login performance"""
    print(f"🧪 Testing Login Performance for {email}...")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "duration": duration,
            "target_met": duration < 2.0,  # Target: under 2 seconds
            "email": email
        }
        
        if result["success"]:
            print(f"✅ Login successful in {duration:.2f}s")
            result["response_data"] = response.json()
        else:
            print(f"❌ Login failed: {response.status_code}")
            try:
                result["error"] = response.json()
            except:
                result["error"] = response.text
        
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Login error after {duration:.2f}s: {e}")
        return {
            "success": False,
            "duration": duration,
            "target_met": False,
            "error": str(e)
        }


def test_admin_login_performance(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test admin login performance"""
    return test_login_performance("admin@ytili.com", "admin123", base_url)


def run_performance_tests():
    """Run comprehensive performance tests"""
    print("🚀 Starting Ytili Authentication Performance Tests")
    print("=" * 60)
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {}
    }
    
    # Test 1: Admin Login Performance
    print("\n📋 Test 1: Admin Login Performance")
    admin_login_result = test_admin_login_performance()
    results["tests"]["admin_login"] = admin_login_result
    
    # Test 2: New User Registration Performance
    print("\n📋 Test 2: New User Registration Performance")
    registration_result = test_registration_performance()
    results["tests"]["registration"] = registration_result
    
    # Test 3: New User Login Performance (if registration succeeded)
    if registration_result.get("success") and "user_email" in registration_result:
        print("\n📋 Test 3: New User Login Performance")
        new_user_login_result = test_login_performance(
            registration_result["user_email"], 
            "TestPassword123!"
        )
        results["tests"]["new_user_login"] = new_user_login_result
    
    # Performance Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for test_name, test_result in results["tests"].items():
        status = "✅ PASS" if test_result.get("target_met", False) else "❌ FAIL"
        duration = test_result.get("duration", 0)
        print(f"{test_name.upper()}: {status} ({duration:.2f}s)")
    
    # Overall Assessment
    all_targets_met = all(test.get("target_met", False) for test in results["tests"].values())
    all_successful = all(test.get("success", False) for test in results["tests"].values())
    
    print("\n🎯 OVERALL ASSESSMENT:")
    if all_targets_met and all_successful:
        print("✅ ALL PERFORMANCE TARGETS MET!")
        print("✅ Registration: < 3 seconds")
        print("✅ Login: < 2 seconds")
        print("✅ System ready for production")
    else:
        print("❌ PERFORMANCE TARGETS NOT MET")
        print("🔧 Further optimization required")
    
    return results


if __name__ == "__main__":
    results = run_performance_tests()
    
    # Save results to file
    with open("auth_performance_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: auth_performance_results.json")
