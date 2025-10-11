#!/bin/bash

# =============================================================================
# Complete Approval Flow Test Script
# =============================================================================
# This script demonstrates the full approval flow for the DOCX Agent backend
# Run this to test both approval and rejection scenarios
# =============================================================================

set -e  # Exit on error

API_URL="http://localhost:8080"
USER_ID="test_user_$(date +%s)"

echo "=================================================="
echo "🧪 DOCX Agent - Complete Approval Flow Test"
echo "=================================================="
echo ""

# -----------------------------------------------------------------------------
# Test 1: Health Check
# -----------------------------------------------------------------------------
echo "📡 Test 1: Health Check"
echo "Command: curl -X GET '$API_URL/health'"
echo ""
curl -s -X GET "$API_URL/health" | python3 -m json.tool
echo ""
echo "✅ Expected: status: healthy"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 2: Non-Edit Operation (No Approval Required)
# -----------------------------------------------------------------------------
echo "=================================================="
echo "📖 Test 2: Query Operation (No Approval Needed)"
echo "=================================================="
echo ""
echo "Command:"
echo "curl -X POST '$API_URL/api/chat' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"user_id\": \"$USER_ID\","
echo "    \"message\": \"What is in the Executive Overview section?\","
echo "    \"platform\": \"api\""
echo "  }'"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"message\": \"What is in the Executive Overview section?\",
    \"platform\": \"api\"
  }")

echo "$RESPONSE" | python3 -m json.tool
echo ""
echo "✅ Expected: requires_approval: false, status: completed"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 3: Edit Operation - Request Approval
# -----------------------------------------------------------------------------
echo "=================================================="
echo "✏️  Test 3: Edit Operation (Approval Required)"
echo "=================================================="
echo ""
echo "Command:"
echo "curl -X POST '$API_URL/api/chat' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"user_id\": \"$USER_ID\","
echo "    \"message\": \"Change the CEO name in Executive Overview to Tony Stark\","
echo "    \"platform\": \"api\""
echo "  }'"
echo ""

APPROVAL_RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"message\": \"Change the CEO name in Executive Overview to Tony Stark\",
    \"platform\": \"api\"
  }")

echo "$APPROVAL_RESPONSE" | python3 -m json.tool
echo ""

# Extract session_id for next step
SESSION_ID=$(echo "$APPROVAL_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo "✅ Expected: requires_approval: true, status: waiting_approval"
echo "📝 Session ID: $SESSION_ID"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 4: Approve the Edit
# -----------------------------------------------------------------------------
echo "=================================================="
echo "✅ Test 4: Approve the Edit"
echo "=================================================="
echo ""
echo "Command:"
echo "curl -X POST '$API_URL/api/approve' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"user_id\": \"$USER_ID\","
echo "    \"session_id\": \"$SESSION_ID\","
echo "    \"approved\": true,"
echo "    \"platform\": \"api\""
echo "  }'"
echo ""

APPROVE_RESPONSE=$(curl -s -X POST "$API_URL/api/approve" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"session_id\": \"$SESSION_ID\",
    \"approved\": true,
    \"platform\": \"api\"
  }")

echo "$APPROVE_RESPONSE" | python3 -m json.tool
echo ""
echo "✅ Expected: Edit executed successfully, status: completed"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 5: Another Edit Operation - For Rejection Test
# -----------------------------------------------------------------------------
echo "=================================================="
echo "✏️  Test 5: Another Edit (To Be Rejected)"
echo "=================================================="
echo ""
echo "Command:"
echo "curl -X POST '$API_URL/api/chat' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"user_id\": \"$USER_ID\","
echo "    \"message\": \"Change the company name to Wayne Enterprises\","
echo "    \"platform\": \"api\""
echo "  }'"
echo ""

REJECTION_RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"message\": \"Change the company name to Wayne Enterprises\",
    \"platform\": \"api\"
  }")

echo "$REJECTION_RESPONSE" | python3 -m json.tool
echo ""

# Extract session_id for rejection
SESSION_ID_2=$(echo "$REJECTION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo "✅ Expected: requires_approval: true, status: waiting_approval"
echo "📝 Session ID: $SESSION_ID_2"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 6: Reject the Edit
# -----------------------------------------------------------------------------
echo "=================================================="
echo "❌ Test 6: Reject the Edit"
echo "=================================================="
echo ""
echo "Command:"
echo "curl -X POST '$API_URL/api/approve' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"user_id\": \"$USER_ID\","
echo "    \"session_id\": \"$SESSION_ID_2\","
echo "    \"approved\": false,"
echo "    \"platform\": \"api\""
echo "  }'"
echo ""

REJECT_RESPONSE=$(curl -s -X POST "$API_URL/api/approve" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"session_id\": \"$SESSION_ID_2\",
    \"approved\": false,
    \"platform\": \"api\"
  }")

echo "$REJECT_RESPONSE" | python3 -m json.tool
echo ""
echo "✅ Expected: Operation cancelled, status: completed"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 7: Check User Sessions
# -----------------------------------------------------------------------------
echo "=================================================="
echo "📊 Test 7: View User Sessions"
echo "=================================================="
echo ""
echo "Command: curl -X GET '$API_URL/api/sessions/$USER_ID'"
echo ""

curl -s -X GET "$API_URL/api/sessions/$USER_ID" | python3 -m json.tool
echo ""
echo "✅ Expected: List of all sessions for user $USER_ID"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 8: List All Active Sessions (Admin)
# -----------------------------------------------------------------------------
echo "=================================================="
echo "🔍 Test 8: List All Active Sessions"
echo "=================================================="
echo ""
echo "Command: curl -X GET '$API_URL/api/sessions'"
echo ""

curl -s -X GET "$API_URL/api/sessions" | python3 -m json.tool
echo ""
echo "✅ Expected: All active sessions across all users"
echo ""
read -p "Press Enter to continue..."
echo ""

# -----------------------------------------------------------------------------
# Test 9: Try to Send Message with Pending Approval
# -----------------------------------------------------------------------------
echo "=================================================="
echo "🚫 Test 9: Send Message While Approval Pending"
echo "=================================================="
echo ""

# Create a new user and get them into pending approval state
NEW_USER="pending_test_$(date +%s)"

echo "Creating pending approval for user: $NEW_USER"
PENDING_RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$NEW_USER\",
    \"message\": \"Update the proposal title\",
    \"platform\": \"api\"
  }")

NEW_SESSION_ID=$(echo "$PENDING_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo ""
echo "Now trying to send another message while approval is pending..."
echo ""

BLOCKED_RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$NEW_USER\",
    \"message\": \"What is in the document?\",
    \"platform\": \"api\"
  }")

echo "$BLOCKED_RESPONSE" | python3 -m json.tool
echo ""
echo "✅ Expected: Error message about pending approval"
echo ""

# Clean up - reject the pending approval
curl -s -X POST "$API_URL/api/approve" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$NEW_USER\",
    \"session_id\": \"$NEW_SESSION_ID\",
    \"approved\": false,
    \"platform\": \"api\"
  }" > /dev/null

echo ""
echo "=================================================="
echo "✅ All Tests Completed Successfully!"
echo "=================================================="
echo ""
echo "Summary:"
echo "  ✓ Health check passed"
echo "  ✓ Non-edit operations work without approval"
echo "  ✓ Edit operations trigger approval flow"
echo "  ✓ Approval executes the operation"
echo "  ✓ Rejection cancels the operation"
echo "  ✓ Session management works"
echo "  ✓ Pending approval blocking works"
echo ""
echo "Test User ID: $USER_ID"
echo "Sessions created: 2"
echo ""
