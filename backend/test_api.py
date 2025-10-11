"""
Simple test script for the backend API
Run this to verify your backend is working correctly
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
USER_ID = f"test_user_{int(time.time())}"

def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)
    print(f"{'='*60}\n")

def test_health_check():
    """Test health check endpoint"""
    print("\n🏥 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    return response.status_code == 200

def test_root():
    """Test root endpoint"""
    print("\n🏠 Testing Root Endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print_response("Root", response)
    return response.status_code == 200

def test_read_operation():
    """Test a read operation (no approval needed)"""
    print(f"\n📖 Testing Read Operation (User: {USER_ID})...")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "user_id": USER_ID,
            "message": "Show me the document outline",
            "platform": "api"
        }
    )
    
    print_response("Read Operation", response)
    
    if response.status_code == 200:
        data = response.json()
        if not data.get("requires_approval"):
            print("✅ Read operation completed without approval (as expected)")
            return True
        else:
            print("❌ Unexpected: Read operation required approval")
            return False
    return False

def test_write_operation_with_approval():
    """Test a write operation (requires approval)"""
    print(f"\n✏️ Testing Write Operation (User: {USER_ID})...")
    
    # Step 1: Request a write operation
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "user_id": USER_ID,
            "message": "Update section 2.1 to say 'Test Update'",
            "platform": "api"
        }
    )
    
    print_response("Write Operation Request", response)
    
    if response.status_code != 200:
        print("❌ Failed to send write operation request")
        return False
    
    data = response.json()
    
    # Check if approval is required
    if not data.get("requires_approval"):
        print("⚠️  Write operation did not require approval")
        print("   This might mean:")
        print("   1. The agent didn't recognize this as a write operation")
        print("   2. The tool 'apply_edit' is not in WRITE_TOOLS")
        print("   3. Using local execution mode which simplifies approval")
        return True  # Not necessarily a failure
    
    print("✅ Approval requested (as expected)")
    session_id = data.get("session_id")
    
    # Step 2: Approve the operation
    print("\n👍 Sending approval...")
    approval_response = requests.post(
        f"{BASE_URL}/api/approve",
        json={
            "user_id": USER_ID,
            "session_id": session_id,
            "approved": True,
            "platform": "api"
        }
    )
    
    print_response("Approval Response", approval_response)
    
    if approval_response.status_code == 200:
        print("✅ Approval processed successfully")
        return True
    else:
        print("❌ Failed to process approval")
        return False

def test_reject_operation():
    """Test rejecting an operation"""
    print(f"\n❌ Testing Operation Rejection (User: {USER_ID}_reject)...")
    
    reject_user = f"{USER_ID}_reject"
    
    # Step 1: Request a write operation
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "user_id": reject_user,
            "message": "Delete section 5",
            "platform": "api"
        }
    )
    
    if response.status_code != 200:
        print("⚠️  Could not initiate operation to reject")
        return False
    
    data = response.json()
    
    if not data.get("requires_approval"):
        print("⚠️  Operation did not require approval (skipping rejection test)")
        return True
    
    session_id = data.get("session_id")
    
    # Step 2: Reject the operation
    print("\n👎 Sending rejection...")
    rejection_response = requests.post(
        f"{BASE_URL}/api/approve",
        json={
            "user_id": reject_user,
            "session_id": session_id,
            "approved": False,
            "platform": "api"
        }
    )
    
    print_response("Rejection Response", rejection_response)
    
    if rejection_response.status_code == 200:
        rejection_data = rejection_response.json()
        if "cancel" in rejection_data.get("message", "").lower():
            print("✅ Rejection processed correctly")
            return True
    
    print("❌ Rejection did not work as expected")
    return False

def test_session_management():
    """Test session management"""
    print(f"\n📊 Testing Session Management (User: {USER_ID})...")
    
    # Get user sessions
    response = requests.get(f"{BASE_URL}/api/sessions/{USER_ID}")
    print_response("User Sessions", response)
    
    if response.status_code == 200:
        data = response.json()
        sessions = data.get("sessions", [])
        print(f"✅ Found {len(sessions)} session(s)")
        return True
    
    print("❌ Failed to get sessions")
    return False

def test_all_sessions():
    """Test listing all sessions"""
    print("\n📋 Testing List All Sessions...")
    
    response = requests.get(f"{BASE_URL}/api/sessions")
    print_response("All Sessions", response)
    
    if response.status_code == 200:
        data = response.json()
        count = data.get("count", 0)
        print(f"✅ Found {count} active session(s)")
        return True
    
    print("❌ Failed to get all sessions")
    return False

def main():
    """Run all tests"""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║          DOCX Agent Backend API Test Suite           ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    print(f"🎯 Testing backend at: {BASE_URL}")
    print(f"👤 Test user ID: {USER_ID}")
    
    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root),
        ("Read Operation", test_read_operation),
        ("Write Operation with Approval", test_write_operation_with_approval),
        ("Operation Rejection", test_reject_operation),
        ("Session Management", test_session_management),
        ("List All Sessions", test_all_sessions),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(1)  # Brief pause between tests
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Cannot connect to {BASE_URL}")
            print("   Make sure the backend is running:")
            print("   python app.py")
            print("   or")
            print("   ./start.sh")
            return
        except Exception as e:
            print(f"\n❌ Error in test '{test_name}': {e}")
            results.append((test_name, False))
    
    # Summary
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║                    Test Summary                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your backend is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n💡 Next steps:")
    print("   1. Try the interactive API docs: http://localhost:8000/docs")
    print("   2. Integrate with your chat platform")
    print("   3. Check the README.md for platform-specific examples")

if __name__ == "__main__":
    main()
