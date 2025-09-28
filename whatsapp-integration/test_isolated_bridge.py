#!/usr/bin/env python3
"""
Quick test for the isolated WhatsApp bridge
"""

import subprocess
import sys
import time
import requests

def test_isolated_bridge():
    print("🧪 Testing Isolated WhatsApp Bridge")
    print("=" * 40)
    
    # Start the bridge in background
    print("🚀 Starting isolated bridge...")
    
    try:
        # Run with conda environment
        proc = subprocess.Popen([
            '/home/arun/anaconda3/envs/rfp-agent/bin/python', 
            'isolated_whatsapp_bridge.py'
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
        )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Test health endpoint
        print("🔍 Testing health endpoint...")
        try:
            response = requests.get("http://localhost:5000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Health check: PASSED")
                data = response.json()
                print(f"   Status: {data.get('status')}")
                print(f"   Twilio: {data.get('twilio')}")
                print(f"   Gemini: {data.get('gemini')}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test RAG endpoint
        print("\n🔍 Testing RAG endpoint...")
        try:
            response = requests.get("http://localhost:5000/test?q=test", timeout=10)
            if response.status_code == 200:
                print("✅ RAG test: PASSED")
            else:
                print(f"❌ RAG test failed: {response.status_code}")
        except Exception as e:
            print(f"❌ RAG test error: {e}")
        
        # Check for database conflicts in logs
        print("\n🔍 Checking for database conflicts...")
        stdout, stderr = proc.communicate(timeout=2)
        
        if "database" not in stderr.lower() and "milvus" not in stderr.lower():
            print("✅ No database conflicts detected")
        else:
            print("⚠️  Database-related messages found in logs")
            
        print("\n🎉 Isolated bridge test complete!")
        
    except subprocess.TimeoutExpired:
        proc.kill()
        print("✅ Bridge started successfully (timeout reached)")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        try:
            proc.terminate()
        except:
            pass

if __name__ == "__main__":
    test_isolated_bridge()