#!/usr/bin/env python3
"""
Direct test - check session and send events
"""

import asyncio
import sys
import os

# Add the backend path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'backend'))

from streaming.streaming_manager import get_streaming_manager

async def direct_test():
    session_id = "004-planning-atelier-s-curiser-l-acc-s-au-dossier-d-un"
    manager = get_streaming_manager()
    
    print("🎯 DIRECT TEST - Checking session and sending events")
    
    # Check session info
    session_info = manager.get_session_info(session_id)
    print(f"📊 Session exists: {session_info is not None}")
    if session_info:
        print(f"📊 Session info: {session_info}")
    
    # Check subscribers
    subscribers = manager._subscribers.get(session_id, set())
    print(f"👥 Subscribers: {len(subscribers)}")
    
    if len(subscribers) > 0:
        print("✅ FOUND SUBSCRIBERS! SENDING CODE!")
        
        await manager.emit_code_change(
            session_id, 
            "DIRECT_TEST.py", 
            '''#!/usr/bin/env python3
"""
🎉 DIRECT TEST! The streaming is working!
"""

def main():
    print("✅ Code display is functional!")
    print("🎯 You should see this code in the frontend!")
    print("🚀 Direct test completed successfully!")
    
    return "DIRECT SUCCESS!"

if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")
'''
        )
        
        print("📤 DIRECT CODE SENT!")
        
    else:
        print("❌ No subscribers - frontend needs to connect")
        print("📝 Please keep the streaming dialog open and check if you see backend logs")

if __name__ == "__main__":
    asyncio.run(direct_test())
