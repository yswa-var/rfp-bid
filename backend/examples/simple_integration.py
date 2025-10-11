"""
Simple Integration Example
Shows how to integrate any chat platform with the backend API
"""

import requests
import time

class DOCXAgentClient:
    """Simple client wrapper for the DOCX Agent Backend API"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_cache = {}
    
    def chat(self, user_id, message, platform="api"):
        """
        Send a message to the agent
        
        Args:
            user_id: Unique identifier for the user
            message: The message text
            platform: Platform identifier (e.g., 'telegram', 'discord')
            
        Returns:
            dict: Response from the agent
        """
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "user_id": user_id,
                "message": message,
                "platform": platform
            }
        )
        response.raise_for_status()
        return response.json()
    
    def approve(self, user_id, session_id, approved=True, platform="api"):
        """
        Respond to an approval request
        
        Args:
            user_id: User identifier
            session_id: Session ID from the approval request
            approved: True to approve, False to reject
            platform: Platform identifier
            
        Returns:
            dict: Response from the agent
        """
        response = requests.post(
            f"{self.base_url}/api/approve",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "approved": approved,
                "platform": platform
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_sessions(self, user_id):
        """Get all sessions for a user"""
        response = requests.get(f"{self.base_url}/api/sessions/{user_id}")
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """Check if the backend is healthy"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()


def example_simple_conversation():
    """Example: Simple conversation without approval"""
    print("\n" + "="*60)
    print("Example 1: Simple Conversation")
    print("="*60)
    
    client = DOCXAgentClient()
    user_id = "example_user_1"
    
    # Send a read-only query
    print(f"\n👤 User: Show me the document outline")
    response = client.chat(user_id, "Show me the document outline")
    
    print(f"\n🤖 Agent: {response['message']}")
    print(f"   Approval required: {response['requires_approval']}")


def example_approval_workflow():
    """Example: Conversation with approval required"""
    print("\n" + "="*60)
    print("Example 2: Approval Workflow")
    print("="*60)
    
    client = DOCXAgentClient()
    user_id = "example_user_2"
    
    # Send a write operation
    print(f"\n👤 User: Update section 2.1 to say 'Company Overview'")
    response = client.chat(user_id, "Update section 2.1 to say 'Company Overview'")
    
    if response['requires_approval']:
        print(f"\n🤖 Agent: {response['message']}")
        print(f"\n⏸️  Operation paused, waiting for approval...")
        
        session_id = response['session_id']
        
        # Simulate user thinking...
        time.sleep(1)
        
        # User approves
        print(f"\n👤 User: yes (approve)")
        approval_response = client.approve(user_id, session_id, approved=True)
        
        print(f"\n🤖 Agent: {approval_response['message']}")
    else:
        print(f"\n🤖 Agent: {response['message']}")
        print("   (No approval was required)")


def example_rejection():
    """Example: Rejecting an operation"""
    print("\n" + "="*60)
    print("Example 3: Rejecting an Operation")
    print("="*60)
    
    client = DOCXAgentClient()
    user_id = "example_user_3"
    
    # Send a potentially dangerous operation
    print(f"\n👤 User: Delete all content from section 5")
    response = client.chat(user_id, "Delete all content from section 5")
    
    if response['requires_approval']:
        print(f"\n🤖 Agent: {response['message']}")
        print(f"\n⏸️  Operation paused, waiting for approval...")
        
        session_id = response['session_id']
        
        # User rejects
        print(f"\n👤 User: no (reject)")
        rejection_response = client.approve(user_id, session_id, approved=False)
        
        print(f"\n🤖 Agent: {rejection_response['message']}")
    else:
        print(f"\n🤖 Agent: {response['message']}")


def example_multi_turn_conversation():
    """Example: Multi-turn conversation"""
    print("\n" + "="*60)
    print("Example 4: Multi-turn Conversation")
    print("="*60)
    
    client = DOCXAgentClient()
    user_id = "example_user_4"
    
    messages = [
        "What's in the document?",
        "Search for 'project timeline'",
        "What sections mention budget?",
    ]
    
    for message in messages:
        print(f"\n👤 User: {message}")
        response = client.chat(user_id, message)
        print(f"🤖 Agent: {response['message'][:200]}...")
        time.sleep(0.5)


def example_platform_integration():
    """Example: How to integrate with a chat platform"""
    print("\n" + "="*60)
    print("Example 5: Platform Integration Pattern")
    print("="*60)
    
    print("""
This is a template for integrating with any chat platform:

```python
from your_platform import Bot, Message

client = DOCXAgentClient()

@bot.on_message
async def handle_message(message: Message):
    # Get user identifier from your platform
    user_id = f"platform_{message.user.id}"
    
    # Send to backend API
    response = client.chat(user_id, message.text, platform="your_platform")
    
    if response['requires_approval']:
        # Show approval UI (buttons, inline keyboard, etc.)
        await message.reply(
            response['message'],
            buttons=[
                Button('Approve', callback_data='approve'),
                Button('Reject', callback_data='reject')
            ]
        )
        
        # Store session_id for when user clicks button
        await store_pending_approval(message.user.id, response['session_id'])
    else:
        # Normal response
        await message.reply(response['message'])

@bot.on_button_click
async def handle_button(button_event):
    user_id = f"platform_{button_event.user.id}"
    session_id = await get_pending_approval(button_event.user.id)
    
    # Process approval
    approved = button_event.data == 'approve'
    result = client.approve(user_id, session_id, approved)
    
    # Update message
    await button_event.edit_message(result['message'])
```
""")


def main():
    """Run all examples"""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║        DOCX Agent Backend Integration Examples        ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Check if backend is running
    try:
        client = DOCXAgentClient()
        health = client.health_check()
        print(f"✅ Backend is healthy (Active sessions: {health['active_sessions']})")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("\nMake sure the backend is running:")
        print("  cd backend")
        print("  python app.py")
        return
    
    examples = [
        example_simple_conversation,
        example_approval_workflow,
        example_rejection,
        example_multi_turn_conversation,
        example_platform_integration,
    ]
    
    for example in examples:
        try:
            example()
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Error in example: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Examples completed!")
    print("="*60)
    print("\n💡 Use these patterns to integrate with your platform:")
    print("   • Telegram: Use python-telegram-bot library")
    print("   • Discord: Use discord.py library")
    print("   • Slack: Use slack-bolt library")
    print("   • WhatsApp: Use twilio or whatsapp-business-api")
    print("   • Custom: Use requests library with your platform's SDK")


if __name__ == "__main__":
    main()
